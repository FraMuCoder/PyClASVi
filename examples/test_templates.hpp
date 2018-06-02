// use this to test
// get_num_template_arguments
// get_template_xxx
namespace test_templates
{
    template <class T, int N, bool B>
    T f1(T a);

    template <>
    int f1<int, 5, true>(int a);

    template <>
    float f1<float, -10, false>(float a);

    template <class T, int N>
    class C1;

    template <>
    class C1<int, 5>;

    template <int N>
    class C1<float, N>;
}
