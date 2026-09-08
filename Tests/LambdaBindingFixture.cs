using System;
using System.Collections.Generic;
using System.Linq;

public static class Program {
    static Dictionary<int, int> Build(int[] values, out List<Func<int>> readers) {
        var groups = values.GroupBy(value => value % 2);
        var result = groups.ToDictionary(grouping => grouping.Key, grouping => grouping.Sum());
        readers = new List<Func<int>>();
        foreach (var grouping in values.GroupBy(value => value / 3)) {
            readers.Add(() => grouping.Key + grouping.Sum());
        }
        foreach (var grouping in values.GroupBy(value => value % 2)) {
            readers.Add(() => 100 + grouping.Key + grouping.Sum());
        }
        return result;
    }
    public static void Main() {
        List<Func<int>> first, second;
        var a = Build(new[] { 1, 2, 3, 4, 7 }, out first);
        var b = Build(new[] { 2, 6 }, out second);
        if (a[0] != 6 || a[1] != 11 || b[0] != 8 || b.Count != 1)
            throw new Exception("Lambda parameters changed");
        if (!first.Select(read => read()).SequenceEqual(new[] { 3, 8, 9, 112, 106 }) ||
            !second.Select(read => read()).SequenceEqual(new[] { 2, 8, 108 }) || first[0]() != 3)
            throw new Exception("Captured groups changed");
        Console.WriteLine("PASS: independent lambda parameters and escaped group captures");
    }
}
