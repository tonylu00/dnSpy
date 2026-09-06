using System;
using System.Collections.Generic;

public static class JumpLocalFixture {
    static int reads, cleanups;
    static readonly Exception Failure = new InvalidOperationException("operand");
    static int Read(int value) { reads++; if (value == -99) throw Failure; return value; }

    static int SwitchJoin(int state, int input, bool alternative) {
        int value;
        try {
            switch (state) {
                case 0: value = Read(input); goto shared;
                case 1: goto independent;
                case 2: value = Read(input) + 17; goto shared;
                case 3: break;
                default: return -1;
            }
            return -2;
            independent:
            return Read(input) * 3;
            shared:
            if (alternative) { input = value * 2; goto independent; }
            return value - 4;
        }
        finally { cleanups++; }
    }

    // A retained state machine recomputes this ordinary local on each resume;
    // it must remain shared by the switch assignments and the labeled reader.
    sealed class Steps : IEnumerator<int> {
        int state, input;
        public Steps(int input) { this.input = input; }
        public int Current { get; private set; }
        object System.Collections.IEnumerator.Current { get { return Current; } }
        public bool MoveNext() {
            int value;
            try {
                switch (state) {
                    case 0: state = -1; value = Read(input); goto shared;
                    case 1: state = -1; goto independent;
                    case 2: state = -1; value = Read(input) + 17; goto shared;
                    case 3: state = -1; break;
                    default: return false;
                }
                return false;
                independent:
                Current = 41; state = 2; return true;
                shared:
                if (value > 10) { Current = value - 4; state = 3; return true; }
                Current = value * 2; state = 1; return true;
            }
            catch { Dispose(); throw; }
        }
        public void Reset() { throw new NotSupportedException(); }
        public void Dispose() { state = -1; cleanups++; }
    }

    public static int Main() {
        int checks = 0;
        foreach (int state in new[] { -1, 0, 1, 2, 3, 4 })
        foreach (int input in new[] { -99, -2, 0, 10, 100 })
        foreach (bool alternative in new[] { false, true }) {
            reads = cleanups = 0;
            try {
                int result = SwitchJoin(state, input, alternative);
                if (input == -99 && state >= 0 && state <= 2) throw new Exception("missing exception");
                int value = input + (state == 2 ? 17 : 0);
                int expected = state < 0 || state > 3 ? -1 : state == 3 ? -2 : state == 1 ? input * 3 : alternative ? value * 6 : value - 4;
                if (result != expected) throw new Exception("join value changed");
            }
            catch (Exception e) { if (!ReferenceEquals(e, Failure)) throw; }
            int expectedReads = state >= 0 && state <= 2 ? 1 : 0;
            if ((state == 0 || state == 2) && alternative && input != -99) expectedReads++;
            if (reads != expectedReads || cleanups != 1) throw new Exception("join effects changed");
            checks++;
        }
        foreach (int input in new[] { -99, 0, 4, 10, 20 }) {
            reads = cleanups = 0;
            var steps = new Steps(input);
            var result = new List<int>();
            try {
                while (steps.MoveNext()) { result.Add(steps.Current); if (result.Count > 4) throw new Exception("iterator failed to terminate"); }
                if (input == -99) throw new Exception("missing iterator exception");
                string expected = input > 10 ? (input - 4).ToString() : (input * 2) + ",41," + (input + 13);
                if (string.Join(",", result) != expected || reads != (input > 10 ? 1 : 2) || cleanups != 0) throw new Exception("iterator resume changed");
            }
            catch (Exception e) {
                if (!ReferenceEquals(e, Failure) || reads != 1 || cleanups != 1) throw;
            }
            if (steps.MoveNext()) throw new Exception("completed iterator resumed");
            steps.Dispose();
            if (cleanups != (input == -99 ? 2 : 1)) throw new Exception("iterator disposal changed");
            checks++;
        }
        Console.WriteLine("PASS: " + checks + " jump-local value, effect, exception, resume and disposal scenarios.");
        return 0;
    }
}
