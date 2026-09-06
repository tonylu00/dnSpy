using System.Linq;
using dnlib.DotNet;
class Emitter {
    static void Main(string[] args) {
        using var module = ModuleDefMD.Load(args[0]);
        var publisher = module.GetTypes().Single(t => t.Name == "Publisher");
        int next = 0;
        foreach (var item in publisher.Events) {
            item.Name = "_event" + next;
            item.AddMethod.Name = "_add" + next;
            item.RemoveMethod.Name = "_remove" + next++;
        }
        // The interface event row remains authoritative even if its accessor
        // methods no longer use the conventional add_/remove_ names.
        var other = module.GetTypes().Single(t => t.Name == "ISecondEvents").Events.Single();
        other.AddMethod.Name = "Subscribe";
        other.RemoveMethod.Name = "Unsubscribe";
        module.Write(args[1]);
    }
}
