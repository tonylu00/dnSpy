using De4dot.NameCandidates;

if (args.Length < 4) throw new ArgumentException("Usage: <contract-manifest> <application-map> <fresh-selected-map> <physical-module-path> [...]");
MapSelection.Write(args[1], args[2], args.Skip(3), args[0]);
