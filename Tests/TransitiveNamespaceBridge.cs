namespace FixtureRoot.Types {
    public class Bus {
        public int Value => global::FixtureRoot.Bus.Cryptography.Secret.Value;
    }
    public class Shared { public int Value => 23; }
    public class Packet<T> { public T Value; }
}
namespace FixtureRoot.Other {
    public class Anchor { public int Value => 17; }
}
