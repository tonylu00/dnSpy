# Signed native-integer arithmetic

Run `Invoke-NativeArithmeticRegression.ps1` with `-DnSpyConsole` and a fresh `-OutputDirectory`. Run both `-Platform AnyCPU` and `-Platform x86` on 64-bit Windows. Requires the .NET 10 SDK and .NET Framework 4.8.

The emitter creates add/sub and signed checked add/sub IL over native integers. Framework IntPtr references do not expose an IntPtr-plus-IntPtr operator usable by C#, so source uses nint casts to retain native-width operations. Pointer arithmetic remains on its existing path. This change covers signed native addition/subtraction, not every native integer opcode or unsigned overflow variant.

The original and rebuilt executables compare edge cases at the current architecture's minimum and maximum values, unchecked wrapping, normal checked results, overflow and underflow. The script checks identical execution width, source determinism with one/four workers, and unchanged inputs. Source containing nint requires a C# 9 or newer compiler.
