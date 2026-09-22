"""Explicit behavior mappings for authenticated routing and its timer state machine.

Usage: python routing_timer.py ARTIFACT_ROOT NEW_63_STEM NEW_64_STEM
Reads physical metadata/source evidence and writes review data only.
"""
from pathlib import Path
import sys
from behavior_review import BehaviorReview, sha
from usb_configuration_write import local_used


def stage(root, stem63, stem64):
    batches = {}
    for version, base, prior, methods in [
        ('63', 187, 'connector-write63-wave187.cumulative.json', 'falcon63-native-wave176-methods.json'),
        ('64', 22, 'connector-write64-wave22.cumulative.json', 'falcon64-native-wave13-methods.json')]:
        batches[version] = BehaviorReview(root, version, base, 'm0088' if version == '63' else 'm0153', {
            'Methods': methods, 'Types': f'resume-falcon{version}-types.json',
            'Fields': f'resume-falcon{version}-fields.json'}, root / prior)

    for version, batch in batches.items():
        is63 = version == '63'
        path = root / f'routing-timer{version}-wave188-inspection.json'
        data = batch.read(path.name)
        assert data['Mvid'] == batch.module['Mvid'] and data['Sha256'] == batch.module['Sha256']
        bodies = {m['Token']: m for m in data['Methods']}

        def method(token, name, reason, parameters=None, locals_=None, evidence=(), counterpart=None, replace_alias=None):
            key = f'0x{0x06000000 + token:08X}'
            body = bodies[key]
            assert body['Signature'] == batch.entries['Methods'][key]['Signature']
            for slot in locals_ or {}:
                expected = next(l['ExpectedType'] for l in batch.entries['Methods'][key]['LocalNames'] if l['Index'] == slot)
                assert next(l['Type'] for l in body['Locals'] if l['Slot'] == slot) == expected and local_used(body, slot)
            batch.add('Methods', 0x06000000 + token, name, reason, parameters, locals_,
                      evidence=[0x06000000 + t for t in evidence], replace_alias=replace_alias)
            assert not batch.pending, batch.pending
            batch.decisions[-1]['IL'] = {'Path': str(path), 'Sha256': sha(path), 'Token': key, 'Slots': locals_ or {}}
            if counterpart:
                batch.decisions[-1]['CounterpartSource'] = batches['64'].source(0x06000000 + counterpart)

        def symbol(kind, token, name, reason, evidence):
            existing = batch.aliases.get((batch.relative, f'0x{token:08X}'))
            if existing is not None and existing.get('NewName') == name:
                return
            batch.add(kind, token, name, reason, evidence=[0x06000000 + t for t in evidence])
            assert not batch.pending, batch.pending

        # Nonce construction and byte transforms precede the frame callers.
        method(0x1AD9 if is63 else 0x3155, 'BuildIpCcmMacBlock',
               'Builds a 16-byte block from a big-endian 48-bit sequence, 48-bit serial number, 16-bit message tag and 16-bit payload length. High sequence bits are discarded.',
               ('sequenceNumber', 'serialNumber', 'messageTag', 'payloadLength'))
        method(0x1ADA if is63 else 0x3156, 'BuildIpCcmCounterBlock',
               'Builds the sequence/serial/tag counter block with byte 14 set to 0xFF and byte 15 initially zero.',
               ('sequenceNumber', 'serialNumber', 'messageTag'))
        method(0x1AD8 if is63 else 0x3154, 'GenerateCounterKeyStream',
               'Clones the initial counter block, encrypts successive blocks with AES-128 ECB and increments only byte 15. Requests over 4096 bytes are rejected. Retains the original stream/padding and disposal behavior.',
               ('key', 'length', 'counterBlock'),
               {0: 'currentCounter', 1: 'aes', 2: 'keyBuffer', 3: 'output', 4: 'encryptingStream', 5: 'blockCount', 6: 'blockIndex'} if is63 else
               {0: 'currentCounter', 2: 'keyBuffer', 12: 'aes', 14: 'output', 16: 'encryptingStream'})
        method(0x1AD7 if is63 else 0x3153, 'CcmDecryptInternal',
               'XORs the encrypted MAC with the start of the counter key stream and the encrypted payload with bytes after the reserved MAC block. Returns payload and outputs the plain MAC separately; this helper does not authenticate either result.',
               ('key', 'encryptedPayload', 'encryptedMac', 'counterBlock', 'plainMac', 'reservedMacBytes'),
               {0: 'keyStream', 1: 'plainPayload'})
        if is63:
            method(0x1AD1, 'IpSecurityCalcUnencryptedCcmMac', 'Builds the IP MAC block and delegates to the existing CBC-MAC helper with unencrypted-MAC output.',
                   ('key', 'header', 'payload', 'sequenceNumber', 'serialNumber', 'messageTag'), {0: 'macBlock'}, (0x1AD9,), 0x314D)
            method(0x1AD4, 'IpSecurityEncryptCcm', 'Builds the IP counter block and delegates to the existing encrypt helper with a 16-byte MAC reservation.',
                   ('key', 'payload', 'plainMac', 'sequenceNumber', 'serialNumber', 'messageTag'), {0: 'counterBlock'}, (0x1ADA,), 0x3150)
            method(0x1AD6, 'IpSecurityDecryptCcm', 'Separates the trailing 16 encrypted MAC bytes, decrypts payload and MAC, then concatenates both plain results. Authentication is performed by the frame caller.',
                   ('key', 'encryptedData', 'sequenceNumber', 'serialNumber', 'messageTag'), {0: 'counterBlock', 1: 'plainMac'}, (0x1AD7, 0x8C8), 0x3152)

            for token, name, reason, counterpart in [
                (0x8C2, 'get_InnerMessageFrame', 'Returns the retained or successfully decrypted inner frame.', 0x131F),
                (0x8C3, 'get_SecureSessionIdentifier', 'Reads the 16-bit session identifier at the frame body start.', 0x1320),
                (0x8C4, 'get_SequenceNumber', 'Reads the six-byte sequence/group timer value at body offset two.', 0x1321),
                (0x8C5, 'get_SerialNumber', 'Reads the six-byte serial number at body offset eight.', 0x1322),
                (0x8C6, 'get_MessageTag', 'Reads the 16-bit message tag at body offset fourteen.', 0x1323),
                (0x8C7, 'get_IsAuthentic', 'Returns successful authentication state, also initialized by keyed outgoing construction.', 0x1324),
                (0x910, 'get_TimeStamp', 'Reads the six-byte timer timestamp from the notification body start.', 0x1399),
                (0x911, 'get_SerialNumber', 'Reads the notification serial number at body offset six.', 0x139A),
                (0x912, 'get_MessageTag', 'Reads the notification message tag at body offset twelve.', 0x139B),
                (0x913, 'get_IsAuthentic', 'Returns the MAC comparison result or the keyed outgoing construction flag.', 0x139C)]:
                method(token, name, reason, (), counterpart=counterpart)
            method(0x8C8, 'DecryptUsingSessionKey', 'Decrypts payload/MAC and compares the received MAC with a recomputed MAC before parsing the inner frame and marking transport security. Caches success; a later different key is only logged and still returns true. Existing behavior is preserved.',
                   ('key',), {0: 'encryptedData', 1: 'plainDataAndMac', 2: 'header', 3: 'plainPayload', 4: 'expectedMac', 5: 'receivedMac'})
            method(0x8C0, None, 'Wraps a received frame and attempts decryption/authentication only when a key is supplied.', ('rawFrame', 'key'), evidence=(0x8C8,))
            method(0x8C1, None, 'Serializes secure-wrapper session/sequence/serial/tag fields; with a key, computes and encrypts payload/MAC and marks the retained inner frame transport-secured.',
                   ('innerFrame', 'sessionIdentifier', 'sequenceNumber', 'serialNumber', 'messageTag', 'key'),
                   {0: 'header', 1: 'plainPayload', 2: 'plainMac', 3: 'encryptedData'})
            method(0x90D, None, 'Wraps the input and, if keyed, compares a calculated notification MAC with the 16 received bytes at absolute offset 20.',
                   ('rawFrame', 'key'), {0: 'expectedMac', 1: 'receivedMac'})
            method(0x90E, None, 'Serializes timer/serial/tag fields; with a key, writes the calculated notification MAC and marks the outgoing frame authentic.',
                   ('timestamp', 'serialNumber', 'messageTag', 'key'), {0: 'encryptedMac'})
            for token, name, proof in [(0xBAC, 'authenticatedKey', 0x8C8), (0xBAD, 'isAuthentic', 0x8C8),
                                        (0xBAE, 'innerFrame', 0x8C1), (0xBC2, 'isAuthentic', 0x90D)]:
                symbol('Fields', 0x04000000 + token, name, 'Frame storage established by construction, authentication and getters.', (proof,))
        method(0x90F if is63 else 0x1398, 'CalculateEncryptedNotificationMac',
               'Calculates the plain IP CCM MAC over the frame header with no payload, then encrypts that MAC using the notification timestamp, serial and message tag.',
               ('key',), {0: 'header', 1: 'plainMac'})

        if is63:
            method(0x1861, None, 'Captures the state and trigger used as a dictionary lookup key.', ('state', 'trigger'))
            method(0x1867, 'SelectTransitionKey', 'Extracts the declared state/trigger pair for construction of the transition lookup. Replaces the reviewed constructor-lambda alias with its actual selector behavior.', ('transition',), replace_alias='<.ctor>b__5_0')
            method(0x185F, None, 'Requires state accessor/mutator, stores the logger, and indexes transitions by state/trigger. Duplicate transition keys retain ToDictionary failure behavior.',
                   ('stateAccessor', 'stateMutator', 'transitions', 'logger'), evidence=(0x1867,))
            method(0x1860, 'Fire', 'Looks up the current state/trigger, runs its action or state-returning action, and logs/mutates state only when changed. Missing transitions do nothing; action failures propagate.',
                   ('instance', 'trigger', 'context'), {0: 'currentState', 1: 'transition', 2: 'nextState'})
            method(0x1868, None, 'Defines a fixed next-state transition with an optional action and explicit/default display name.',
                   ('state', 'trigger', 'newState', 'action', 'name'))
            method(0x1869, None, 'Defines a transition whose action computes the next state; initializes fallback next state to the current state.',
                   ('state', 'trigger', 'actionDeterminingNewState', 'name'))
            for token, name in [(0x440, 'Knx.Falcon.Impl.Utilities.StateMachine'), (0x441, 'TransitionKey'), (0x442, 'TransitionKeySelector')]:
                symbol('Types', 0x02000000 + token, name, 'Generic transition lookup/execution helper used by the timer and other physical callers.', (0x185F, 0x1860, 0x1867))
            for first, names, proof in [(0x13D0, 'stateAccessor stateMutator logger transitions', 0x1860),
                                         (0x13D5, 'state trigger', 0x1861),
                                         (0x13D7, 'Instance selectTransitionKey', 0x185F),
                                         (0x13DA, 'state trigger newState action actionDeterminingNewState name', 0x1868)]:
                for offset, name in enumerate(names.split()):
                    symbol('Fields', 0x04000000 + first + offset, name, 'Transition infrastructure storage traced through constructors, lookup, actions and accessors.', (proof, 0x1869))

        # Timestamp context and low-level timer helpers precede transition actions.
        for token, name, reason in [(0, 'get_Timestamp', 'Returns the event timestamp.'),
                                    (1, 'get_SerialNumber', 'Returns the event serial number used to identify synchronization replies.'),
                                    (2, 'get_MessageTag', 'Returns the event message tag used to correlate synchronization replies.'),
                                    (3, 'get_IsAccepted', 'Returns the acceptance decision set by the transition action.'),
                                    (4, 'set_IsAccepted', 'Stores the acceptance decision returned by ReceivedSecureWrapper.')]:
            method((0x1DCF if is63 else 0x35E5) + token, name, reason, ('value',) if token == 4 else ())
        method(0x1DCE if is63 else 0x35E4, None, 'Captures timestamp, serial number and message tag for timer/secure-wrapper transition processing.', ('timestamp', 'serialNumber', 'messageTag'))
        symbol('Types', 0x0200054B if is63 else 0x020006D8, 'TimerEventContext', 'Timestamp, serial/tag correlation and mutable secure-wrapper acceptance result passed through timer transitions.', (0x1DCE, 0x1DC2, 0x1DC3) if is63 else (0x35E4, 0x35D6, 0x35D7))
        for offset, name in enumerate('timestamp serialNumber messageTag isAccepted'.split()):
            symbol('Fields', (0x04001B17 if is63 else 0x0400254E) + offset, name, 'Event context storage traced through its constructor and accessors.', (0x1DCE, 0x1DD3) if is63 else (0x35E4, 0x35E9))
        method(0x1DC9 if is63 else 0x35DD, 'GetUtcMilliseconds', 'Converts the timing abstraction UTC time to unsigned Unix milliseconds.', (), {0: 'utcTime'})
        method(0x1DCB if is63 else 0x35DF, 'ChooseNotifyDelay', 'Chooses an inclusive random delay between the bounds; when maximum is no greater than minimum returns maximum. Retains the int range conversion.', ('minimum', 'maximum'))
        method(0x1DCC if is63 else 0x35E0, 'SetupNotifyTimer', 'Promotes zero delay to one, stops the timer, divides the interval by the timing speed factor, records update/periodic purpose and restarts the one-shot timer.', ('delayMilliseconds', 'isUpdateNotify'))
        method(0x1DC1 if is63 else 0x35D5, 'SendTimerNotifyAsync', 'Clears the update-scheduled flag and invokes the send callback. Replies reuse the captured request serial/tag; ordinary notifications generate a new random tag and use the local serial. Callback exceptions fault the task.',
               ('timestamp', 'replyContext'), {0 if is63 else 1: 'stateMachine'}, (0x1DDA,) if is63 else ())
        method(0x1DD6 if is63 else 0x35EF, 'ReadCurrentState', 'State-machine accessor reads the stored state directly.', ('timer',))
        method(0x1DD7 if is63 else 0x35F0, 'WriteCurrentState', 'State-machine mutator writes the stored state directly; logging belongs to the generic transition executor.', ('timer', 'state'))
        symbol('Types', 0x0200054C if is63 else 0x020006D9, 'TimerStateAccessors', 'Cached state-access delegates supplied to the generic transition executor.', (0x1DD6, 0x1DD7) if is63 else (0x35EF, 0x35F0))

        if is63:
            props = [
                (0x1D8B, 'MinDelayPeriodicNotify', 'Selects the time-keeper or time-follower minimum periodic delay.'),
                (0x1D8C, 'MaxDelayPeriodicNotify', 'Selects the time-keeper or time-follower maximum periodic delay.'),
                (0x1D8D, 'MinDelayUpdateNotify', 'Selects the time-keeper or time-follower minimum update delay.'),
                (0x1D8E, 'MaxDelayUpdateNotify', 'Selects the time-keeper or time-follower maximum update delay.'),
                (0x1D93, 'ConnectMode', 'Reads the configured backbone timer synchronization trust mode.'),
                (0x1D95, 'LatencyTolerance', 'Reads the received-frame age tolerance.'),
                (0x1D97, 'SyncLatencyTolerance', 'Reads the close-synchronization tolerance used in timestamp classification and derived delays.'),
                (0x1D99, 'MinDelayInitialNotify', 'Reads the lower initial-notification delay bound.'),
                (0x1D9B, 'MaxDelayInitialNotify', 'Reads the upper initial-notification delay bound.'),
                (0x1D9D, 'MinDelayTimeKeeperPeriodicNotify', 'Reads the minimum periodic delay for a time keeper.'),
                (0x1D9F, 'MaxDelayTimeKeeperPeriodicNotify', 'Returns keeper periodic minimum plus three synchronization tolerances.'),
                (0x1DA0, 'MinDelayTimeFollowerPeriodicNotify', 'Returns keeper periodic maximum plus one synchronization tolerance.'),
                (0x1DA1, 'MaxDelayTimeFollowerPeriodicNotify', 'Returns follower periodic minimum plus ten synchronization tolerances.'),
                (0x1DA2, 'MinDelayTimeKeeperUpdateNotify', 'Reads the minimum update-notification delay for a time keeper.'),
                (0x1DA4, 'MaxDelayTimeKeeperUpdateNotify', 'Returns keeper update minimum plus one synchronization tolerance.'),
                (0x1DA5, 'MinDelayTimeFollowerUpdateNotify', 'Returns keeper update maximum plus one synchronization tolerance.'),
                (0x1DA6, 'MaxDelayTimeFollowerUpdateNotify', 'Returns follower update minimum plus ten synchronization tolerances.'),
                (0x1DAC, 'IsTimeKeeper', 'Reads whether this instance currently acts as the time keeper.'),
                (0x1DAE, 'IsUpdateNotifyScheduled', 'Reads whether the pending one-shot timer is for an update reply.'),
                (0x1DC7, 'CurrentState', 'Reads the stored notification scheduling state.')]
            setters = {0x1D93, 0x1D95, 0x1D97, 0x1D99, 0x1D9B, 0x1D9D, 0x1DA2, 0x1DAC, 0x1DAE}
            for token, name, reason in props:
                method(token, 'get_' + name, reason, ())
                if token in setters:
                    method(token + 1, 'set_' + name, 'Stores the ' + name + ' setting consumed by the reviewed timer logic.', ('value',))
            method(0x1DC8, 'set_CurrentState', 'Logs and stores a state change only if it differs from the current state.', ('value',))
            method(0x1D91, 'get_GroupTimer', 'Applies artificial clock skew relative to its base, adds the timer offset and masks to the low 48 bits.', (), {0: 'currentMilliseconds'})
            method(0x1D92, 'set_GroupTimer', 'Resets the skew reference to current time and adjusts the offset to make the group timer equal the supplied value.', ('value',))
            method(0x1DA9, 'SetArtificialClockSkew', 'Changes the parts-per-million skew and resets its time base while retaining the current group timer value.', ('partsPerMillion',), {0: 'currentGroupTimer'})
            method(0x1DAA, 'AddArtificialTimeOffset', 'Adds an artificial millisecond offset; clamps a negative adjustment so the current group timer cannot become negative.', ('offsetMilliseconds',), {0: 'currentGroupTimer'})
            method(0x1DAB, 'get_InternalState', 'Encodes the time-keeper bit and scheduling state shifted by eight for diagnostics.', (), {0: 'encodedState'})
            method(0x1DCA, 'UpdateGroupTimer', 'Only advances the group timer, logs its delta and increments the configured statistic when a collector exists.', ('timestamp',), {0: 'currentGroupTimer', 1: 'statisticsUpdate'})
            method(0x1D90, None, 'Stores the notification callback, local serial and statistics context; initializes tolerances, one-shot timer and group timer zero.', ('sendTimerNotify', 'ownSerialNumber', 'statistics', 'updateTimerStatisticIndex'))
            method(0x1DA7, 'ScheduleInitialTimerNotifyAsync', 'With a nonzero initial maximum, schedules a randomized initial notification under the state lock. Otherwise sends immediately, then schedules a periodic notification. Records the initial time for synchronization waits.', (), {0: 'stateMachine'}, (0x1DD8,))
            method(0x1DA8, 'WaitForValidResponseAsync', 'Unless unsynchronized mode is configured, waits for a correlated/trusted response, forces one additional notification after the first timeout and waits again. Timeouts are swallowed; this method can complete without a valid response.', (), {0: 'stateMachine'}, (0x1DDC,))

        actions = [
            ('LogIgnoredTransition', 'Only writes the existing A0 diagnostic; leaves timer/context unchanged.'),
            ('UpdateTimerAndCheckSyncResponse', 'Advances to the context timestamp. Completes synchronization only for a matching local serial/tag or trust-first-response mode.'),
            ('AcceptSecureWrapper', 'Marks the context accepted; ReceivedSecureWrapper returns this result.'),
            ('SchedulePeriodicNotify', 'Chooses a periodic delay for the current keeper/follower role and arms a non-update notification.'),
            ('ScheduleUpdateReply', 'Retains the triggering context and arms an update reply with a randomized role-dependent delay.'),
            ('SendPeriodicNotify', 'Starts a notification with the context timestamp and no reply identity. The returned task is deliberately not awaited here.'),
            ('SendPendingUpdateReply', 'Starts a notification using the retained request identity, then clears it. The task is not awaited here.'),
            ('ScheduleInitialNotify', 'Arms a non-update notification using the configured initial-delay range.'),
            ('BecomeTimeKeeper', 'Sets the time-keeper role flag.'),
            ('BecomeTimeFollower', 'Clears the time-keeper role flag.'),
            ('SynchronizeAndScheduleFollowerNotify', 'Updates/checks synchronization, becomes a follower, then schedules a periodic notification.'),
            ('BecomeFollowerAndSchedulePeriodicNotify', 'Becomes a follower and schedules the next periodic notification.'),
            ('UpdateTimerAcceptWrapperAndSchedulePeriodicNotify', 'Updates/checks synchronization, accepts the wrapper, then schedules a periodic notification.'),
            ('UpdateTimerAndAcceptWrapper', 'Updates/checks synchronization and accepts the wrapper, retaining the current notification schedule.'),
            ('AcceptWrapperAndSchedulePeriodicNotify', 'Accepts the wrapper and schedules a periodic notification.'),
            ('SendNotifyAndScheduleTimeKeeper', 'Starts an ordinary notification, becomes time keeper and schedules a periodic notification without awaiting the send.'),
            ('ReplyAndScheduleTimeKeeper', 'Starts the pending update reply, becomes time keeper and schedules a periodic notification without awaiting the send.')]
        for offset, (name, reason) in enumerate(actions):
            method((0x1DB0 if is63 else 0x35C4) + offset, name, reason, ('timer', 'context'))

        if is63:
            for token, name, reason, scopes in [
                (0x1DC2, 'ReceivedTimerNotify', 'Under the state lock, classifies the received timestamp as ahead, within sync tolerance, within latency tolerance or too old, and fires the corresponding notification trigger.', {0: 'context', 1: 'syncRoot', 2: 'lockTaken', 3: 'currentGroupTimer'}),
                (0x1DC3, 'ReceivedSecureWrapper', 'Uses the same four timestamp categories under the state lock, fires the corresponding wrapper trigger and returns the context acceptance flag. This is age/state gating, not per-sender duplicate tracking.', {0: 'context', 1: 'syncRoot', 2: 'lockTaken', 3: 'currentGroupTimer', 4: 'accepted'})]:
                method(token, name, reason, ('timestamp', 'serialNumber', 'messageTag'), scopes)
            method(0x1DC4, 'SentSecureWrapper', 'Fires the sent-wrapper trigger under the state lock with the supplied timestamp and no reply identity.', ('timestamp',), {0: 'syncRoot', 1: 'lockTaken'})
            method(0x1DCD, 'NotifyTimerElapsed', 'Under the state lock, fires the elapsed trigger only for periodic/update scheduling states. Logs and swallows exceptions from processing.', ('sender', 'eventArgs'), {0: 'syncRoot', 1: 'lockTaken', 2: 'error'})
            # E11 has no observed firing caller; retain that enum label rather
            # than inventing the missing event's domain meaning.
            trigger_names = ['TimerNotifyAhead', 'TimerNotifyWithinSyncTolerance', 'TimerNotifyWithinLatencyTolerance', 'TimerNotifyTooOld',
                             'SecureWrapperAhead', 'SecureWrapperWithinSyncTolerance', 'SecureWrapperWithinLatencyTolerance', 'SecureWrapperTooOld',
                             'SecureWrapperSent', 'NotificationTimerElapsed']
            for offset, name in enumerate(trigger_names):
                symbol('Fields', 0x04001B0C + offset, name, 'Trigger meaning established by actual timestamp branches or send/timer callbacks and the transition table.', (0x1DC2, 0x1DC3, 0x1DC4, 0x1DCD, 0x1D8F))
            timer_fields = [
                (0x1AEB, 'logger'), (0x1AEC, 'stateMachine'), (0x1AED, 'currentState'), (0x1AEE, 'syncRoot'),
                (0x1AEF, 'groupTimerOffset'), (0x1AF0, 'notifyTimer'), (0x1AF1, 'validResponseCompletion'),
                (0x1AF2, 'hasValidResponse'), (0x1AF3, 'initialNotificationTime'), (0x1AF4, 'sendTimerNotify'),
                (0x1AF5, 'ownSerialNumber'), (0x1AF6, 'lastNotificationTag'), (0x1AF7, 'statistics'),
                (0x1AF8, 'updateTimerStatisticIndex'), (0x1AF9, 'clockSkewBaseTime'), (0x1AFA, 'clockSkewPartsPerMillion'),
                (0x1AFB, 'connectMode'), (0x1AFC, 'latencyTolerance'), (0x1AFD, 'syncLatencyTolerance'),
                (0x1AFE, 'minDelayInitialNotify'), (0x1AFF, 'maxDelayInitialNotify'), (0x1B00, 'minDelayTimeKeeperPeriodicNotify'),
                (0x1B01, 'minDelayTimeKeeperUpdateNotify'), (0x1B02, 'isTimeKeeper'), (0x1B03, 'isUpdateNotifyScheduled'),
                (0x1B04, 'pendingReplyContext'), (0x1B05, 'transitions'), (0x1B1C, 'Instance')]
            for token, name in timer_fields:
                symbol('Fields', 0x04000000 + token, name, 'Timer storage role traced through initialization, timing calculations, transition actions and async send/wait bodies.', (0x1D8F, 0x1D90, 0x1D91, 0x1DB1, 0x1DD8, 0x1DDA, 0x1DDC))
            for type_token, name, start, fields, proof in [
                (0x54D, 'ScheduleInitialTimerNotifyAsyncState', 0x1B1E, 'state builder timer awaiter', (0x1DA7, 0x1DD8)),
                (0x54E, 'SendTimerNotifyAsyncState', 0x1B23, 'state builder timer replyContext timestamp awaiter', (0x1DC1, 0x1DDA)),
                (0x54F, 'WaitForValidResponseAsyncState', 0x1B2A, 'state builder timer responseAwaiter sendAwaiter', (0x1DA8, 0x1DDC)),
                (0x545, 'SendTimerNotifyAsyncState', 0x1AD5, 'state builder connector timestamp serialNumber messageTag awaiter', (0x1D5D, 0x1D85))]:
                symbol('Types', 0x02000000 + type_token, name, 'Async operation state carrier; explicit IAsyncStateMachine methods and unused storage stay intact.', proof)
                for offset, field in enumerate(fields.split()):
                    symbol('Fields', 0x04000000 + start + offset, field, 'Used state storage traced through the wrapper and complete MoveNext body.', proof)

        # Route authenticated/timed frames outward to the receive notification.
        method(0x1D5F if is63 else 0x3550, 'NextMessageTag', 'Returns the current 16-bit tag and increments it with wraparound; does not add synchronization.', (), {0: 'messageTag'})
        method(0x1D5B if is63 else 0x354C, 'WrapOutgoingRoutingFrame', 'With a routing key, records secure-send statistics, allocates a message tag, captures group time, constructs an authenticated wrapper and notifies the timer of that send. Otherwise records a plain send and returns the original frame.',
               ('frame',), {0: 'messageTag', 1 if is63 else 7: 'timestamp'})
        method(0x1D5C if is63 else 0x354D, 'HandleTimerNotify', 'When a routing key exists, records notification statistics and forwards timestamp/serial/tag to the group timer. The caller has already checked authenticity.', ('notification',))
        method(0x1D56 if is63 else 0x3547, 'HandleRoutingPayloadFrame', 'Returns messages carried by routing indication/system-broadcast frames. Busy frames update send pacing under the connector lock; lost/unknown frames update diagnostics and return null. Unknown frames invoke the unhandled-frame delegate.',
               ('frame',), {0: 'indication', 1: 'systemBroadcast', 2: 'lostMessage', 4: 'busyFrame', 6: 'syncRoot', 7: 'lockTaken'} if is63 else
               {11: 'indication', 1: 'systemBroadcast', 13: 'lostMessage', 16: 'busyFrame', 6: 'syncRoot', 17: 'lockTaken'})
        method(0x1D55 if is63 else 0x3546, 'HandleReceivedDataFrame', 'Applies system-broadcast policy, enforces configured secure/plain frame mode, validates wrapper/notification authentication and group-timer acceptance, then dispatches the inner/plain payload. Records each rejection and retains existing unhandled-frame callback behavior.',
               ('frame',), {0: 'isSecureFrame', 1 if is63 else 21: 'secureWrapper', 2: 'timerNotify', 6 if is63 else 14: 'innerFrame'})
        method(0x1D54 if is63 else 0x3545, 'DispatchReceivedRoutingFrame', 'Processes a frame, suppresses one echo matching the pending confirmation by source/destination/length/APCI, then emits raw data and bus-message events outside Info mode. The comparison does not compare payload bytes.',
               ('frame',), {0: 'message', 1 if is63 else 4: 'shouldDeliver', 2: 'pendingConfirmation', 3: 'busMessage'})
        if is63:
            method(0x1D5D, 'SendTimerNotifyAsync', 'With a routing key and connected communication, counts the outgoing notification, waits for send pacing and transmits a keyed timer notification. Missing security/communication returns successfully; asynchronous failures propagate.',
                   ('timestamp', 'serialNumber', 'messageTag'), {0: 'stateMachine'}, (0x1D85,))
            for token, name, evidence in [(0x1A60, 'secureGroupTimer', (0x1D55, 0x1D5B)),
                                         (0x1A61, 'routingKey', (0x1D5B, 0x1D85)),
                                         (0x1A63, 'nextMessageTag', (0x1D5F,)),
                                         (0x1A64, 'pendingConfirmation', (0x1D54, 0x1D87)),
                                         (0x1A66, 'statistics', (0x1D55, 0x1D5B)),
                                         (0x1A88, 'unhandledFrame', (0x1D55, 0x1D56))]:
                symbol('Fields', 0x04000000 + token, name, 'Connector storage consumed by the reviewed authenticated routing send/receive path.', evidence)

        assert not batch.pending
        batch.save(stem63 if is63 else stem64)


if __name__ == '__main__':
    stage(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
