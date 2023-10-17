import unittest
from hypothesis import given, settings, Verbosity
from hypothesis import strategies as st

class TestGenerationSeed(unittest.TestCase):
    @settings(verbosity=Verbosity.verbose)
    @given(new_var0=st.integers(), new_var1=st.integers(), new_var2=st.booleans(), new_var3=st.booleans(), new_var4=st.text(), new_var5=st.text(), new_var6=st.text(), new_var7=st.none(), new_var8=st.text(), new_var9=st.text(), new_var10=st.text(), new_var11=st.text(), new_var12=st.text(), new_var13=st.text(), new_var14=st.text(), new_var15=st.text(), new_var16=st.text(), new_var17=st.integers(), new_var18=st.integers(), new_var19=st.text(), new_var20=st.integers(), new_var21=st.floats(), new_var22=st.integers(), new_var23=st.integers(), new_var24=st.integers(), new_var25=st.integers(), new_var26=st.text(), new_var27=st.text(), new_var28=st.text(), new_var29=st.text(), new_var30=st.text(), new_var31=st.text(), new_var32=st.text(), new_var33=st.text(), new_var34=st.integers(), new_var35=st.integers(), new_var36=st.integers(), new_var37=st.integers(), new_var38=st.integers(), new_var39=st.integers(), new_var40=st.text(), new_var41=st.integers(), new_var42=st.integers(), new_var43=st.integers(), new_var44=st.integers(), new_var45=st.integers(), new_var46=st.integers(), new_var47=st.integers(), new_var48=st.integers(), new_var49=st.integers(), new_var50=st.integers(), new_var51=st.integers(), new_var52=st.integers(), new_var53=st.text(), new_var54=st.text())
    def test_generation_seed(self, new_var0, new_var1, new_var2, new_var3,
        new_var4, new_var5, new_var6, new_var7, new_var8, new_var9, new_var10,
        new_var11, new_var12, new_var13, new_var14, new_var15, new_var16,
        new_var17, new_var18, new_var19, new_var20, new_var21, new_var22,
        new_var23, new_var24, new_var25, new_var26, new_var27, new_var28,
        new_var29, new_var30, new_var31, new_var32, new_var33, new_var34,
        new_var35, new_var36, new_var37, new_var38, new_var39, new_var40,
        new_var41, new_var42, new_var43, new_var44, new_var45, new_var46,
        new_var47, new_var48, new_var49, new_var50, new_var51, new_var52,
        new_var53, new_var54):
        self.assertEqual(1, new_var0)
        self.assertNotEqual(1, new_var1)
        self.assertTrue(new_var2)
        self.assertFalse(new_var3)
        self.assertIs('hi', new_var4)
        self.assertIsNot('hi', new_var5)
        self.assertIsNone(new_var6)
        self.assertIsNotNone(new_var7)
        self.assertIn('beans', [new_var8, new_var9])
        self.assertIn(new_var10, ['eggs', 'fish'])
        self.assertNotIn('beans', [new_var11, new_var12, new_var13])
        self.assertNotIn(new_var14, ['beans', 'eggs', 'fish'])
        self.assertIsInstance(new_var15, int)
        self.assertNotIsInstance(new_var16, str)
        with self.assertRaises(ValueError):
            my_var = new_var17 + new_var18
        with self.assertRaisesRegexp(ValueError, 'foo'):
            raise ValueError(new_var19)
        self.assertAlmostEqual(3, new_var20)
        self.assertNotAlmostEqual(3, new_var21)
        self.assertGreater(0, new_var22)
        self.assertGreaterEqual(0, new_var23)
        self.assertLess(1, new_var24)
        self.assertLessEqual(1, new_var25)
        self.assertRegexpMatches('bot', new_var26)
        self.assertRegexpMatches(new_var27, 'bat')
        self.assertNotRegexpMatches('bot', new_var28)
        self.assertNotRegexpMatches(new_var29, 'bot')
        self.assertCountEqual([new_var30, new_var31], [new_var32, new_var33])
        with self.assertWarns(UserWarning):
            my_var = new_var34 + new_var35
        with self.assertWarnsRegex(RuntimeWarning, 'oh no'):
            my_var = new_var36 + new_var37
        with self.assertLogs('foo', level='INFO') as cm:
            my_var = new_var38 + new_var39
        a = """this
        is
        a
        string"""
        b = new_var40
        self.assertMultiLineEqual(a, b)
        self.assertSequenceEqual([0, 5, 10], [new_var41, new_var42, new_var43])
        self.assertListEqual([0, 5, 10], [new_var44, new_var45, new_var46])
        self.assertTupleEqual((0, 5, 10), (new_var47, new_var48, new_var49))
        self.assertSetEqual({0, 5, 10}, {new_var50, new_var51, new_var52})
        self.assertDictEqual({'foo': 'bar'}, {new_var53: new_var54})
    