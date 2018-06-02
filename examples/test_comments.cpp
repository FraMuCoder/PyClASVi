// use this to test
// brief_com,ent
// raw_comment
namespace test_comments
{
    /// @brief Class c1
    /// And more comment
    class c1
    {
    public:
        c1();           ///< constructor
        /** Function f2 */
        int f2();
        /**
         * This is Member m2,
         * and it's type is float.
         * This is all you need.
         */
        float m2;
    protected:
        // \brief Comment 1
        // \return An integer
        int f3(int a); ///< Comment 2
        bool m3;
    private:
        /**
         * \brief Function f3
         * \return An other integer
         */
        int f4();
        /**
         * Member m4
         */
        double m4;
    };
}
