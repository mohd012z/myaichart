import tempfile
import unittest
from pathlib import Path
from clone_manifest_rewrite import rewrite
from clone_manifest_audit import audit

OLD="net.metaquotes.metatrader5"
NEW="com.msa.mt5research"
XML=f'''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="{OLD}">
<permission android:name="{OLD}.permission.INTERNAL"/>
<application android:name="{OLD}.Terminal">
<provider android:name="{OLD}.Provider" android:authorities="{OLD}.provider;third.party" android:readPermission="{OLD}.permission.INTERNAL"/>
<activity android:name="{OLD}.MainActivity" android:taskAffinity="{OLD}"/>
</application></manifest>'''
class RewriteTests(unittest.TestCase):
    def test_rewrite_keeps_class_identity_and_changes_scoped_names(self):
        with tempfile.TemporaryDirectory() as d:
            src,dst=Path(d)/"original.xml",Path(d)/"clone.xml"
            src.write_text(XML)
            rewrite(src,dst)
            result=audit(src,dst,NEW)
            self.assertTrue(result["passed"],result)
            value=dst.read_text()
            self.assertIn(NEW+".provider;third.party",value)
            self.assertIn(OLD+".MainActivity",value)
            self.assertIn(OLD+".Terminal",value)
            self.assertIn(OLD+".Provider",value)
            self.assertEqual(src.read_text(),XML)
    def test_refuses_in_place(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"original.xml";p.write_text(XML)
            with self.assertRaises(ValueError):rewrite(p,p)
if __name__=="__main__":unittest.main()
