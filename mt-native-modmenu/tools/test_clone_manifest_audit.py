import tempfile
import unittest
from pathlib import Path
from clone_manifest_audit import audit

A = 'http://schemas.android.com/apk/res/android'
def manifest(pkg, authority, permission=None):
    perm = ('<permission android:name="' + permission + '"/>' if permission else '')
    return ('<manifest xmlns:android="' + A + '" package="' + pkg + '">' + perm +
            '<application><provider android:name="x.Provider" android:authorities="' +
            authority + '"/></application></manifest>')

class CloneManifestTests(unittest.TestCase):
    def run_audit(self, original, clone):
        with tempfile.TemporaryDirectory() as d:
            a, b = Path(d)/'original.xml', Path(d)/'clone.xml'
            a.write_text(original); b.write_text(clone)
            return audit(a,b,'com.msa.mt5research')
    def test_distinct_identity_passes(self):
        r=self.run_audit(manifest('net.metaquotes.metatrader5','old.authority'),
                         manifest('com.msa.mt5research','new.authority'))
        self.assertTrue(r['passed'],r)
    def test_same_package_fails(self):
        r=self.run_audit(manifest('net.metaquotes.metatrader5','old'),
                         manifest('net.metaquotes.metatrader5','new'))
        self.assertIn('UNCHANGED_PACKAGE',r['errors'])
    def test_authority_collision_fails(self):
        r=self.run_audit(manifest('net.metaquotes.metatrader5','old'),
                         manifest('com.msa.mt5research','old'))
        self.assertTrue(any('PROVIDER_AUTHORITY_COLLISION' in x for x in r['errors']))
    def test_declared_permission_collision_fails(self):
        r=self.run_audit(manifest('net.metaquotes.metatrader5','old','custom.perm'),
                         manifest('com.msa.mt5research','new','custom.perm'))
        self.assertTrue(any('DECLARED_PERMISSION_COLLISION' in x for x in r['errors']))
if __name__ == '__main__':
    unittest.main()
