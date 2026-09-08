using System;
public static class LoopEntryFixture {
    public static int Run(bool alternate) {
        int state, result = 0, remaining = 3;
        if (alternate) goto InitializeB;
        goto InitializeA;
    Dispatch:
        switch (state) {
        case 0:
            result += 2;
            state = 1;
            goto Dispatch;
        case 1:
            if (--remaining > 0) {
                state = 0;
                goto Dispatch;
            }
            return result;
        case 2:
            result += 3;
            state = 1;
            goto Dispatch;
        default:
            return -1;
        }
    InitializeA:
        state = 0;
        goto Dispatch;
    InitializeB:
        state = 2;
        goto Dispatch;
    }
    public static int Main() {
        for (int i = 0; i < 20; i++) {
            if (Run(false) != 6 || Run(true) != 7) throw new Exception("Loop entry changed");
        }
        Console.WriteLine("PASS: both external dispatcher entries preserve iteration state");
        return 0;
    }
}
