from sgtk.platform import Application

class BacthPublisherTextureApp(Application):
    def init_app(self):
        app_payload = self.import_module("app")
        menu_callback = lambda: app_payload.batchpublishertexture.show_dialog(self)
        self.engine.register_command("Batch Publisher Texture...", menu_callback)