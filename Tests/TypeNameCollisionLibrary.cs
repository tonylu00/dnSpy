using System;

namespace TypeNameCollisions {
    public class Alpha {
        public int AlphaMethod(int value) { return value + 1; }
        public string AlphaMethod(string value) { return value + "!"; }
        public class Slot {
            public int Value = 17;
            public class Child { public int Value = 23; }
        }
        public class GenericSlot<T> {
            public T Value;
            public GenericSlot(T value) { Value = value; }
        }
        public int Lookup() { return new Slot().Value; }
        public int Lookup(int value) { return value + new Slot.Child().Value; }
        public static string Reflect() {
            return typeof(Alpha).FullName + "|" + typeof(Slot).FullName + "|" +
                typeof(Alpha).GetMethod("Alpha", new[] { typeof(int) }).Invoke(new Alpha(), new object[] { 4 });
        }
    }
}
