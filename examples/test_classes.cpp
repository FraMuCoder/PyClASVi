// use this to test
// access_specifier
// get_arguments
// is_const_method
// is_mutable_field
// is_pure_virtual_methode
// is_static_methode
// is_virtual_methode
// result_type
namespace test_classes
{
    class c1
    {
        // this is private
        void f1(int a);
        int m1;
    public:
        c1();
        int f2() const;
        virtual void v1() = 0;
        virtual void v2();
        static void s1();
        float m2;
    protected:
        const int * f3(const int a);
        bool m3;
    private:
        void f4();
        mutable double m4;
    };

    struct s1
    {
        // this is public
        void f1(int * a);
        int m1;
    public:
        s1(const int * a);
        int f2(int const * a);
        float m2;
    protected:
        int f3(int * const a);
        bool m3;
    private:
        void f4(int const * const a);
        double m4;
    };

    void c1::f1(int a) {}
    c1::c1() {}
    int c1::f2() const { return 0; }
    void c1::v2() {}
    void c1::s1() {}
    const int * c1::f3(int a) { return 0; }
    void c1::f4() {}

    void s1::f1(int * a) {}
    s1::s1(const int * a) {}
    int s1::f2(int const * a) { return 0; }
    int s1::f3(int * const a) { return 0; }
    void s1::f4(int const * const a) {}
}
