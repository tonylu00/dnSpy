"""Protect heavy ETS work with free-space reserves and an owned output forecast.

No cleanup, source edits, hard links, or detached/background commands. Run from
the main checkout so historical producer files and their evidence pins stay intact.
Migration callers should select --budget-policy advisory: an estimate overrun
warns and revises the forecast, while actual free-space reserves remain mandatory.
The legacy hard policy remains available for callers requiring an explicit ceiling.
"""
import argparse
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

GIB = 1024 ** 3
SCRATCH = Path('D:/knx_analysis/workflow-scratch')


def space_status():
    if os.name != 'nt':
        return []
    rows=[]
    for root,reserve in [('C:/',10),('D:/',15)]:
        free=shutil.disk_usage(root).free
        rows.append(dict(Volume=root,FreeBytes=free,FreeGiB=round(free/GIB,2),ReserveGiB=reserve))
    return rows


def require_space(output, additional_bytes=0, observed=None):
    """Reserve includes the peak additional allocation, not just input size."""
    output = Path(output).resolve()
    rows=space_status() if observed is None else observed
    for row in rows:
        needed = row['ReserveGiB'] * GIB
        if output.drive.casefold() == Path(row['Volume']).drive.casefold():
            needed += additional_bytes
        if row['FreeBytes'] < needed:
            raise RuntimeError(f"Storage guard: {row['Volume']} needs {needed / GIB:.2f} GiB free "
                               f"including reserve; only {row['FreeGiB']:.2f} GiB available. "
                               "Run the reviewed cleanup manually or reduce/reuse the work. "
                               "Heavy work is blocked; existing output is preserved.")
    return rows


def tree_bytes(root):
    total = 0
    stack = [Path(root)] if Path(root).exists() else []
    while stack:
        folder = stack.pop()
        if folder.is_symlink() or (hasattr(folder, 'is_junction') and folder.is_junction()):
            raise RuntimeError(f'Linked output is not budgetable: {folder}')
        try:
            entries = list(folder.iterdir())
        except FileNotFoundError:
            continue  # A build can remove its own transient directory.
        for entry in entries:
            try:
                if entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction()):
                    raise RuntimeError(f'Linked output is not budgetable: {entry}')
                if entry.is_dir():
                    stack.append(entry)
                elif entry.is_file():
                    total += entry.stat().st_size
            except FileNotFoundError:
                continue
    return total


def validate_output(output, scratch=SCRATCH, resume=False):
    output, scratch = Path(output).absolute(), Path(scratch).absolute()
    # Check links before resolve(), which would otherwise hide a junction.
    for part in (output, *output.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise RuntimeError(f'Linked output ancestor: {part}')
    output, scratch = output.resolve(), scratch.resolve()
    if output.parent != scratch or output.name.startswith('.'):
        raise RuntimeError(f'Use one named block directly under {scratch}; never the system-disk worktree.')
    if output.exists() and not resume:
        raise RuntimeError('Output exists. Reuse its evidence, or explicitly --resume the same owned block.')
    return output


def stop_owned(process):
    if process.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    else:
        process.kill()
    process.wait(timeout=30)


def replace_sample(sample, receipt, *, timeout=1):
    """Allow short Windows readers to close without discarding telemetry.

    A reader can deny delete sharing while the receipt is open. Keep the last
    complete receipt available and retry only that sharing/access failure.
    Permanent permission failures still stop the owned producer.
    """
    deadline=time.monotonic()+timeout
    retries=0
    while True:
        try:
            os.replace(sample,receipt)
            return retries
        except PermissionError as error:
            if os.name!='nt' or error.winerror not in (5,32,33) or time.monotonic()>=deadline:
                raise
            retries+=1
            time.sleep(.01)


def forecast_overrun(info, used, phase, headroom_percent):
    """Retain bounded warning telemetry, never turn a forecast into a quota."""
    if used <= info['CurrentForecastBytes']:
        return
    previous = info['CurrentForecastBytes']
    revised = used + math.ceil(used * headroom_percent / 100)
    event = dict(Phase=phase, ObservedBytes=used, PreviousForecastBytes=previous,
                 ReestimatedPeakBytes=revised)
    info['CurrentForecastBytes'] = revised
    info['ForecastExceeded'] = True
    info['ForecastOverrunCount'] += 1
    if info['FirstForecastOverrun'] is None:
        info['FirstForecastOverrun'] = event
    info['LatestForecastOverrun'] = event
    try:
        print(f"Storage guard warning: output {used} bytes exceeded the {previous}-byte "
              f"forecast; revised estimate {revised} bytes. Free-space reserves remain enforced.",
              file=sys.stderr, flush=True)
    except (OSError, ValueError):
        # A closed diagnostic stream does not convert a healthy forecast overrun
        # into a quota failure. The structured receipt still retains the warning.
        info['ForecastWarningOutputFailed'] = True


def run_bounded(command, output, budget_bytes, *, resume=False, scratch=SCRATCH, interval=2,
                budget_policy='hard', forecast_headroom_percent=25):
    output = validate_output(output, scratch, resume)
    if budget_bytes <= 0:
        raise ValueError('An explicit positive peak output budget is required')
    if budget_policy not in ('hard', 'advisory'):
        raise ValueError('Budget policy must be hard or advisory')
    if not math.isfinite(forecast_headroom_percent) or forecast_headroom_percent <= 0:
        raise ValueError('Forecast headroom must be a finite positive percentage')
    initial = tree_bytes(output)
    if initial > budget_bytes and budget_policy == 'hard':
        raise RuntimeError('Existing block already exceeds the requested budget')
    headroom = (math.ceil(max(initial, budget_bytes) * forecast_headroom_percent / 100)
                if budget_policy == 'advisory' else 0)
    additional = max(0, budget_bytes - initial) + headroom
    initial_space=require_space(output, additional)
    # Only one guarded heavy producer runs at once. A stale lock is preserved
    # for explicit inspection; it is never automatically stolen.
    registry = Path(scratch) / '.storage'
    registry.mkdir(parents=True, exist_ok=True)
    lock = registry / 'active.lock'
    receipt = registry / (time.strftime('%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8] + '.json')
    info = dict(Kind='StorageBoundedRun', Output=str(output), BudgetBytes=budget_bytes,
                BudgetPolicy=budget_policy, CurrentForecastBytes=budget_bytes,
                ForecastHeadroomPercent=forecast_headroom_percent if budget_policy == 'advisory' else 0,
                PreflightHeadroomBytes=headroom, PreflightAdditionalBytes=additional,
                ForecastExceeded=False, ForecastOverrunCount=0,
                FirstForecastOverrun=None, LatestForecastOverrun=None,
                InitialBytes=initial, Command=command, LauncherPid=os.getpid(), Status='preparing',
                SampledPeakBytes=initial,SampleCount=0,SamplingIntervalSeconds=interval,
                ReceiptReplacementRetries=0,
                MinimumObservedFreeBytes={row['Volume']:row['FreeBytes'] for row in initial_space},
                PeakMeasurementScope='Logical file lengths observed during polling; transient peaks between samples are not measured')
    with lock.open('x', encoding='utf-8') as stream:
        json.dump(info, stream)
    process = None

    def observe(phase):
        used = tree_bytes(output)
        info['SampledPeakBytes'] = max(info['SampledPeakBytes'], used)
        info['SampleCount'] += 1
        rows = space_status()
        for row in rows:
            volume, free = row['Volume'], row['FreeBytes']
            info['MinimumObservedFreeBytes'][volume] = min(
                info['MinimumObservedFreeBytes'].get(volume, free), free)
        # During execution only the actual reserves are hard stops. A revised
        # forecast may need more headroom without constituting a reserve breach.
        require_space(output, observed=rows)
        if budget_policy == 'advisory':
            forecast_overrun(info, used, phase, forecast_headroom_percent)
        elif used > budget_bytes:
            if phase == 'terminal':
                raise RuntimeError('Terminal output exceeds the requested budget')
            raise RuntimeError(f'Output budget exceeded: {used / GIB:.2f} > {budget_bytes / GIB:.2f} GiB')
        return used

    try:
        if budget_policy == 'advisory':
            forecast_overrun(info, initial, 'resume', forecast_headroom_percent)
        process = subprocess.Popen(command, env=dict(os.environ, DOTNET_ADD_GLOBAL_TOOLS_TO_PATH='false'))
        info.update(ChildPid=process.pid, Status='running')
        receipt.write_text(json.dumps(info, indent=2), encoding='utf-8')
        while True:
            used = observe('running')
            # The receipt is telemetry, not the exclusive ownership lock. A
            # replacement keeps readers from observing a partially written sample.
            sample=receipt.with_suffix('.sample.tmp')
            sample.write_text(json.dumps(info,indent=2),encoding='utf-8')
            info['ReceiptReplacementRetries']+=replace_sample(sample,receipt)
            code = process.poll()
            if code is not None:
                # A fast producer can write and exit after the preceding size
                # sample. Its terminal footprint must be sampled again.
                used=observe('terminal')
                info.update(Status='finished' if code == 0 else 'failed', ExitCode=code, FinalBytes=used)
                return code
            time.sleep(interval)
    except BaseException as error:
        if process is not None:
            try:
                stop_owned(process)
            except BaseException as cleanup_error:
                info.update(Status='cleanup-failed', Error=str(error), CleanupError=str(cleanup_error))
                raise
        info.update(Status='stopped', Error=str(error))
        raise
    finally:
        receipt.write_text(json.dumps(info, indent=2), encoding='utf-8')
        # Never admit a second writer while our acquired child may still be live.
        # A failed settlement retains the lock for explicit ownership inspection.
        if process is None or process.poll() is not None:
            lock.unlink()  # Only the tiny lock created by this invocation.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('status')
    run = sub.add_parser('run')
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('--budget-gib', type=float, required=True, help='Estimated peak output, in GiB')
    run.add_argument('--budget-policy', choices=('hard', 'advisory'), default='hard',
                     help='advisory warns/re-estimates; hard retains the legacy explicit ceiling')
    run.add_argument('--forecast-headroom-percent', type=float, default=25,
                     help='Additional preflight headroom for advisory forecasts (default: 25)')
    run.add_argument('--resume', action='store_true')
    run.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.action == 'status':
        rows=space_status()
        print(json.dumps(dict(Volumes=rows, ScratchRoot=str(SCRATCH),
                             HeavyWorkReady=all(r['FreeBytes'] >= r['ReserveGiB'] * GIB for r in rows))))
        return 0
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('Supply the non-detaching command after --')
    if not math.isfinite(args.budget_gib) or args.budget_gib <= 0:
        parser.error('--budget-gib must be finite and positive')
    return run_bounded(command, args.output, int(args.budget_gib * GIB), resume=args.resume,
                       budget_policy=args.budget_policy,
                       forecast_headroom_percent=args.forecast_headroom_percent)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(2)
