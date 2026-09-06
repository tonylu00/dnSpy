using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;
using dnlib.DotNet;

static class DuplicateAssemblyGuards {
    sealed class Fallback : IAssemblyResolver {
        public int Calls;
        public ModuleDef LastSource;
        public AssemblyDef Resolve(IAssembly assembly, ModuleDef source) { Calls++; LastSource=source; return null; }
    }
    static int checks;
    static void Check(bool result,string message) {
        if(!result) throw new Exception(message);
        Interlocked.Increment(ref checks);
    }
    static int Main(string[] args) {
        try { Run(args); return 0; }
        catch(Exception e) { Console.Error.WriteLine(e); return 1; }
    }
    static void Run(string[] args) {
        var runtime=args[0]; var deployment=args[1];
        AppDomain.CurrentDomain.AssemblyResolve+=(sender,e)=> {
            var path=Path.Combine(runtime,new AssemblyName(e.Name).Name+".dll");
            return File.Exists(path)?Assembly.LoadFrom(path):null;
        };
        var helper=Assembly.LoadFrom(Path.Combine(runtime,"dnSpy.Console.exe")).GetType("dnSpy_Console.InputAssemblyResolver",true);
        var paths=new[]{"Runner.exe","plugins\\Plugin.dll","Library.dll","compat\\v1\\Runner.exe","compat\\v1\\plugins\\Plugin.dll","compat\\v1\\Library.dll","Library_orig.dll"};
        var modules=paths.Select(p=>ModuleDefMD.Load(Path.Combine(deployment,p))).ToArray();
        try {
            AssemblyDef withoutSource=null;
            foreach(var order in new[]{modules,modules.Reverse().ToArray()}) {
                var fallback=new Fallback();
                var resolver=(IAssemblyResolver)Activator.CreateInstance(helper,fallback,order);
                foreach(var module in modules) module.Context=new ModuleContext { AssemblyResolver=resolver,Resolver=new Resolver(resolver) };
                foreach(int start in new[]{0,3}) {
                    Check(ReferenceEquals(resolver.Resolve(modules[start+1].Assembly,modules[start]),modules[start+1].Assembly),"local plugin selected");
                    Check(ReferenceEquals(resolver.Resolve(modules[start+2].Assembly,modules[start]),modules[start+2].Assembly),"local library selected");
                    Check(ReferenceEquals(resolver.Resolve(modules[start+2].Assembly,modules[start+1]),modules[start+2].Assembly),"plugin selected parent library");
                    var payload=modules[start+1].GetTypeRefs().Single(t=>t.Name==(start==0?"RootPayload`1":"CompatPayload`1"));
                    Check(ReferenceEquals(payload.ResolveTypeDef().Module,modules[start+2]),"decompiler type resolution follows project references");
                }
                foreach(var module in modules)
                    Check(ReferenceEquals(resolver.Resolve(new AssemblyNameInfo(module.Assembly),module),module.Assembly),"self reference escaped its own input, including backup");
                var noSource=resolver.Resolve(modules[2].Assembly,null);
                Check(noSource==modules[2].Assembly || noSource==modules[5].Assembly,"source-less selection used backup");
                if(withoutSource!=null) Check(ReferenceEquals(noSource,withoutSource),"source-less fallback depends on load order");
                withoutSource=noSource;
                var mixedCase=new AssemblyNameInfo(modules[2].Assembly) { Name="LIBRARY" };
                Check(ReferenceEquals(resolver.Resolve(mixedCase,modules[0]),modules[2].Assembly),"identity case comparison changed");
                Parallel.For(0,256,i=> {
                    int start=i%2==0?0:3;
                    Check(ReferenceEquals(resolver.Resolve(modules[start+2].Assembly,modules[start+1]),modules[start+2].Assembly),"parallel source-scoped cache mixed deployments");
                });
                foreach(var mismatch in new[]{
                    new AssemblyNameInfo(modules[2].Assembly) { Version=new Version(2,0,0,0) },
                    new AssemblyNameInfo(modules[2].Assembly) { Culture="de-DE" },
                    new AssemblyNameInfo(modules[2].Assembly) { PublicKeyOrToken=new PublicKeyToken("0123456789abcdef") },
                    new AssemblyNameInfo("NotExported, Version=1.0.0.0, Culture=neutral, PublicKeyToken=null") }) {
                    int calls=fallback.Calls;
                    Check(resolver.Resolve(mismatch,modules[0])==null,"different identity was substituted");
                    Check(fallback.Calls==calls+1 && ReferenceEquals(fallback.LastSource,modules[0]),"fallback lost source context");
                }
            }
            var backupOnly=(IAssemblyResolver)Activator.CreateInstance(helper,new Fallback(),new[]{modules[6]});
            Check(ReferenceEquals(backupOnly.Resolve(modules[2].Assembly,modules[0]),modules[6].Assembly),"sole explicitly selected backup could not be exported");
            Console.WriteLine("PASS: "+checks+" dependency identity, type resolution, self-reference and parallel-cache checks.");
        }
        finally { foreach(var module in modules) module.Dispose(); }
    }
}
