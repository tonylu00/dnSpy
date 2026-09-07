#using <mscorlib.dll>
using namespace System::Reflection;
[assembly: AssemblyVersionAttribute("1.0.0.0")];
[assembly: System::Runtime::Versioning::TargetFrameworkAttribute(".NETFramework,Version=v4.8")];

#pragma managed(push, off)
__declspec(noinline) int ComputeNative() {
    volatile int value = NATIVE_RESULT;
    return value;
}
#pragma managed(pop)

public ref class NativeBridge abstract sealed {
public:
    static int Read() { return ComputeNative(); }
};
