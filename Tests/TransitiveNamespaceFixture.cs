using System;
namespace FixtureRoot.App {
    public interface IFactory {
        global::FixtureRoot.Types.Bus Create();
    }
    public class Factory : IFactory {
        public global::FixtureRoot.Other.Anchor Anchor = new global::FixtureRoot.Other.Anchor();
        public global::FixtureRoot.Types.Shared Shared = new global::FixtureRoot.Types.Shared();
        public global::FixtureRoot.Types.Bus Create() => new global::FixtureRoot.Types.Bus();
        public global::FixtureRoot.Types.Packet<global::FixtureRoot.Types.Bus[]> Wrap(global::FixtureRoot.Types.Bus value) =>
            new global::FixtureRoot.Types.Packet<global::FixtureRoot.Types.Bus[]> { Value = new[] { value } };
    }
    public static class TransitiveNamespaceFixture {
        static int checks;
        static void Check(bool value) { checks++; if (!value) throw new Exception("Type binding changed: " + checks); }
        public static void Main() {
            var factory = new Factory();
            IFactory contract = factory;
            var bus = contract.Create();
            Check(bus.Value == 41);
            Check(bus.GetType() == typeof(global::FixtureRoot.Types.Bus));
            Check(factory.Shared.Value == 23);
            Check(factory.Shared.GetType() == typeof(global::FixtureRoot.Types.Shared));
            Check(factory.Anchor.Value == 17);
            var wrapped = factory.Wrap(bus);
            Check(ReferenceEquals(wrapped.Value[0], bus));
            Check(wrapped.GetType().GetGenericArguments()[0] == typeof(global::FixtureRoot.Types.Bus[]));
            Console.WriteLine("PASS: " + checks + " transitive namespace and type bindings.");
        }
    }
}
