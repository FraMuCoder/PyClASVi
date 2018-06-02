// use this to test
// kind
// storage_class

namespace
{
    int var_a = 4;
}

static int var_b = 5;

namespace test_code
{
    extern int rnd();

    static int s1 = var_a;

    void f1(void)
    {
        int a;
        int b = 1;
        auto c = 2;

        a = b + c;

        static int d = 0;

        for (int i = 0; i < 10; ++i)
            d += rnd();

        volatile int e = var_b;

        #pragma clang diagnostic push
        #pragma clang diagnostic ignored "-Wdeprecated-register"
        register int i;
        #pragma clang diagnostic pop
        for (i = 0; i < 10; ++i)
            ++e;

        s1 = d + e;
    }
}
