// use this to test
// get_bitfield_width
// get_field_offset
// is_anonymous
// is_bitfield
// type
namespace test_fields
{
    typedef struct {
        bool b1;
        bool b2;
        bool b3;
    } s0_t;

    union u1
    {
        s0_t s0;
        struct s1_t
        {
            int a : 1;
            int b : 2;
            int c : 3;
            int d : 4;
            int x : 16;
        } s1;
        struct
        {
            int   i;
            float f;
            struct
            {
                int    *p1;
                void   *p2;
                double *p3;
            }; // realy anonymous
        } s2;
        struct s4
        {
            int i1;
            int i2;
        }; // anonymous?
    };
}
