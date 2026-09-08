using System;
using System.Windows;
using System.Threading.Tasks;
public class RoutedSource : UIElement {
    public static readonly RoutedEvent ChangedEvent = EventManager.RegisterRoutedEvent("Changed", RoutingStrategy.Direct, typeof(RoutedEventHandler), typeof(RoutedSource));
    public event RoutedEventHandler Changed { add { AddHandler(ChangedEvent, value); } remove { RemoveHandler(ChangedEvent, value); } }
    public void Raise() { RaiseEvent(new RoutedEventArgs(ChangedEvent)); }
}
public class AutoSource {
    public event Action Changed;
    public static event Action Global;
    public void Raise() { Changed?.Invoke(); }
    public static void RaiseGlobal() { Global?.Invoke(); }
    public void Clear() { Changed = null; }
    public static void ClearGlobal() { Global = null; }
}
public class GenericAuto<T> {
    public event Action<T> Changed;
    public void Raise(T value) { Changed?.Invoke(value); }
}
public class SuffixAuto {
    public event Action Changed;
    public void Raise() { Changed?.Invoke(); }
}
public class CustomSource {
    Action ChangedEvent;
    public int Effects;
    public event Action Changed {
        add { Effects++; ChangedEvent += value; }
        remove { Effects += 10; ChangedEvent -= value; }
    }
    public void Raise() { ChangedEvent?.Invoke(); }
}
public class CollisionSource {
    public Action storage;
    public int ChangedField = 7, ChangedField1 = 9;
    public int Effects;
    public event Action Changed {
        add { Effects++; storage += value; }
        remove { Effects += 10; storage -= value; }
    }
    public void Raise() { storage?.Invoke(); }
}
public class SharedStorage {
    static Action storage;
    public event Action Changed {
        add { storage += value; }
        remove { storage -= value; }
    }
    public void Raise() { storage?.Invoke(); }
}
public static class InitializerState {
    public static int Stage, Raised;
    public static Action Prepare() { Stage = 1; return () => Raised++; }
}
public class InitializerBase {
    public InitializerBase() { if (InitializerState.Stage != 1) throw new Exception("event initializer moved past base constructor"); }
}
public class InitializedAuto : InitializerBase {
    public event Action Changed = InitializerState.Prepare();
    public void Raise() { Changed?.Invoke(); }
}
public static class Program {
    [STAThread]
    public static int Main() {
        try { return Run(); }
        catch (Exception error) { Console.Error.WriteLine(error.Message); return 99; }
    }
    static int Run() {
        int count = 0;
        Action handler = () => count++;
        var routed = new RoutedSource();
        RoutedEventHandler routedHandler = (s, e) => { if (!ReferenceEquals(s, routed) || e.RoutedEvent != RoutedSource.ChangedEvent) throw new Exception("routed event identity"); count++; };
        routed.Changed += routedHandler; routed.Raise(); routed.Changed -= routedHandler; routed.Raise();
        if (count != 1) return 1;
        var automatic = new AutoSource();
        automatic.Changed += handler; automatic.Raise(); automatic.Changed -= handler; automatic.Raise();
        AutoSource.Global += handler; AutoSource.RaiseGlobal(); AutoSource.Global -= handler; AutoSource.RaiseGlobal();
        if (count != 3) return 2;
        int cleared = 0;
        Action clearHandler = () => cleared++;
        automatic.Changed += clearHandler; automatic.Clear(); automatic.Raise();
        AutoSource.Global += clearHandler; AutoSource.ClearGlobal(); AutoSource.RaiseGlobal();
        if (cleared != 0) throw new Exception("event storage clearing changed");
        var generic = new GenericAuto<int>();
        Action<int> genericHandler = value => count += value;
        generic.Changed += genericHandler; generic.Raise(5); generic.Changed -= genericHandler; generic.Raise(100);
        if (count != 8) return 3;
        var suffix = new SuffixAuto();
        suffix.Changed += handler; suffix.Raise(); suffix.Changed -= handler; suffix.Raise();
        if (count != 9) return 4;
        var custom = new CustomSource();
        custom.Changed += handler; custom.Raise(); custom.Changed -= handler; custom.Raise();
        if (count != 10 || custom.Effects != 11) return 5;
        var collision = new CollisionSource();
        collision.Changed += handler; collision.Raise(); collision.Changed -= handler; collision.Raise();
        if (count != 11 || collision.Effects != 11 || collision.ChangedField != 7 || collision.ChangedField1 != 9) return 6;
        collision.storage = handler; collision.Raise(); collision.storage = null; collision.Raise();
        if (count != 12 || collision.Effects != 11) return 7;
        var initialized = new CollisionSource { storage = handler };
        initialized.Raise(); initialized.storage = null;
        if (count != 13) return 8;
		Parallel.For(0, 64, i => automatic.Changed += handler);
		automatic.Raise();
		if (count != 77) return 9;
		Parallel.For(0, 64, i => automatic.Changed -= handler);
		automatic.Raise();
		if (count != 77) return 10;
        var shared = new SharedStorage();
        var other = new SharedStorage();
        shared.Changed += handler; other.Raise(); other.Changed -= handler; shared.Raise();
        if (count != 78) return 11;
        var initializedAuto = new InitializedAuto();
        initializedAuto.Raise();
        if (InitializerState.Raised != 1) return 12;
        Console.WriteLine("PASS: routed, automatic, generic and custom event storage preserves dispatch, removal, identity and accessor effects.");
        return 0;
    }
}
