using System;
public sealed class FilterFieldFixture {
    public object Observed;
    public static object GlobalObserved;
    public static int Order;
    public bool Accept, Fail;
    public static void Record(int digit) { Order = Order * 10 + digit; }
    public bool Predicate() { Record(1); if (Fail) throw new FormatException(); return Accept; }
    public bool Run(Exception error) { return false; }
    public static int Main() {
        foreach (bool accept in new[] { false, true }) foreach (bool fail in new[] { false, true }) {
            var fixture = new FilterFieldFixture { Accept = accept, Fail = fail };
            var error = new InvalidOperationException();
            Order = 0; GlobalObserved = null;
            bool selected = fixture.Run(error);
            if (selected != (accept && !fail) || Order != (selected ? 123 : 124) ||
                !ReferenceEquals(fixture.Observed, error) || !ReferenceEquals(GlobalObserved, error))
                throw new Exception("Filter storage, first-pass order or handler selection changed");
        }
        Console.WriteLine("PASS: filter field stores survive rejection, failure and unwind");
        return 0;
    }
}
