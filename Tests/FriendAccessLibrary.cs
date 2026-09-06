using System;

namespace FriendAccess {
    internal enum ValueKind { Number = 7, Text = 11 }
    internal struct Value<T> {
        internal readonly T Item;
        internal readonly ValueKind Kind;
        internal Value(T item, ValueKind kind) { Item = item; Kind = kind; }
    }
    internal interface IReader<T> { T Read(Value<T> value); }
    public sealed class Envelope {
        internal readonly Value<int> Number;
        public Envelope(int number) { Number = new Value<int>(number + 100, ValueKind.Text); }
        internal Envelope(Value<int> number) { Number = number; }
        internal int Read(IReader<int> reader) { return reader.Read(Number); }
        public int Kind { get { return (int)Number.Kind; } }
    }
    internal static class Callbacks {
        internal static int Invoke(Func<Value<int>, int> callback, int value) {
            return callback(new Value<int>(value, ValueKind.Number));
        }
    }
}
