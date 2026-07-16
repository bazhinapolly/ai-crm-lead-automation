from __future__ import annotations
import json, os, socket, tempfile, unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from tests import support  # noqa: F401
from app import build_server
from config import Settings
from seed_data import load_samples
import seed_data

class ConfigAndStartupTests(unittest.TestCase):
    def test_settings_from_env_accepts_documented_values(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"HOST":"127.0.0.1","PORT":"8090","CRM_DATA_DIR":directory,"MAX_REQUEST_BYTES":"2048","MAX_MESSAGE_CHARS":"500","STORE_RAW_MESSAGE":"1","USE_OPENAI":"1","OPENAI_API_KEY":"secret","OPENAI_MODEL":"model-test","OPENAI_TIMEOUT_SECONDS":"15"},clear=True): settings=Settings.from_env()
        self.assertEqual(settings.port,8090); self.assertEqual(settings.data_dir,Path(directory).resolve()); self.assertTrue(settings.store_raw_message); self.assertTrue(settings.use_openai)
    def test_settings_reject_invalid_host_boolean_port_and_missing_key(self):
        cases=[({"HOST":"0.0.0.0"},"loopback"),({"HOST":"localhost"},"numeric loopback"),({"PORT":"0"},"between"),({"USE_OPENAI":"maybe"},"must be 0 or 1"),({"USE_OPENAI":"1"},"OPENAI_API_KEY")]
        for env,message in cases:
            with self.subTest(env=env),patch.dict(os.environ,env,clear=True):
                with self.assertRaisesRegex(ValueError,message): Settings.from_env()
    def test_server_bootstrap_binds_and_releases_an_ephemeral_port(self):
        with tempfile.TemporaryDirectory() as directory:
            server=build_server(Settings(port=0,data_dir=Path(directory))); self.assertGreater(server.server_port,0); server.server_close()
    def test_occupied_port_fails_deterministically(self):
        with tempfile.TemporaryDirectory() as directory,socket.socket() as occupied:
            occupied.bind(("127.0.0.1",0)); occupied.listen(1)
            with self.assertRaises(OSError): build_server(Settings(port=occupied.getsockname()[1],data_dir=Path(directory)))
    def test_seed_loader_validates_corrupt_and_malformed_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"samples.json"; path.write_text("not-json",encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"readable JSON"): load_samples(path)
            path.write_text(json.dumps([{"source":"form"}]),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"source and message"): load_samples(path)
            path.write_text(json.dumps([{"source":"form","message":"Need CRM"}]),encoding="utf-8"); self.assertEqual(load_samples(path)[0]["source"],"form")
    def test_seed_main_resets_and_creates_all_validated_samples(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); (root/"data").mkdir(); (root/"data"/"sample_messages.json").write_text(json.dumps([{"source":"form","message":"Need CRM"},{"source":"chat","message":"Need reporting"}]),encoding="utf-8")
            store=MagicMock(); settings=Settings(data_dir=root/"runtime")
            with patch.object(seed_data,"ROOT_DIR",root),patch.object(seed_data.Settings,"from_env",return_value=settings),patch.object(seed_data,"build_store",return_value=store),patch("builtins.print"): seed_data.main()
            store.reset.assert_called_once_with(); self.assertEqual(store.create_lead.call_count,2)

if __name__ == "__main__": unittest.main()
