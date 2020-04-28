#!python2
# -*- coding:utf-8 -*-
#coding=gbk

import sgtk
import os, sys, threading
import busyDialog
import time, pprint
import Queue
import ctypes, inspect
from sgtk.platform.pyqt import QtCore, QtGui, QtWidgets
logger = sgtk.platform.get_logger(__name__)

sg = sgtk.get_authenticated_user().create_sg_connection()

def show_dialog(app_instance):
    app_instance.engine.show_dialog("Batch Publisher Texture...", app_instance, BatchPublisherTextureUI)

def _async_raise(tid, exctype):
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")

class BatchPublisherTextureUI(QtWidgets.QWidget):
    aim_project_base_path = u'B:/project/s4_chinatravelogues/assets'
    base_path = os.path.dirname(__file__)
    assets = []
    upload_assets = []
    def __init__(self):
        super(BatchPublisherTextureUI, self).__init__()
        logger.info('Launching Batch Publisher Texture...')
        self.busy = busyDialog.BusyDialog(self, '%s/icons/loading_30px.gif' % self.base_path)
        self.loading_worker = LoadingWorker(self.aim_project_base_path, self)
        self.loading_worker.trigger.connect(self.showBusy)
        self.loading_worker.trigger_add_item.connect(self.createItem)
        self.loading_worker.trigger.emit(False)
        self.loading_worker.trigger_other.connect(self.set_other)
        self.loading_worker.trigger_info.connect(self.busy.set_info)
        self.loading_worker.trigger_direction.connect(self.busy.set_progress_direction)
        self.upload_worker = UploadWorker(self)
        self.upload_worker.trigger.connect(self.updateStatus)
        self.upload_worker.trigger_info.connect(self.busy.set_info)
        self.upload_worker.trigger_vis_busy.connect(self.showBusy)
        self.upload_worker.trigger_other.connect(self.set_pub_other)
        self.upload_worker.trigger_direction.connect(self.busy.set_progress_direction)
        self.resize(700,800)
        self.setWindowFlags(QtCore.Qt.Window)
        self.mainLayout = QtWidgets.QVBoxLayout(self)
        self.mainLayout.setContentsMargins(20,5,20,20)
        self.mainLayout.setSpacing(5)

        self.toolsLayout = QtWidgets.QHBoxLayout()
        self.toolsLayout.setContentsMargins(0,0,0,0)
        self.toolsLayout.setSpacing(15)
        self.toolsLayout.setAlignment(QtCore.Qt.AlignLeft)

        self.treeWidget = QtWidgets.QTreeWidget()
        self.treeWidget.setIconSize(QtCore.QSize(15,15))
        self.treeWidget.setHeaderLabels([u'File Name', u'Task Name', u'Pub Status', u'Ver Status'])
        self.treeWidget.setColumnCount(4)
        self.treeWidget.setColumnWidth(0, 400)
        self.treeWidget.setColumnWidth(1, 80)
        self.treeWidget.setColumnWidth(2, 80)
        self.treeWidget.setColumnWidth(3, 80)
        self.treeWidget.setRootIsDecorated(False)
        self.treeWidget.setHeaderHidden(False)
        self.treeWidget.setStyleSheet("QTreeView{ outline:0px;}")

        self.queryButton = QtWidgets.QPushButton()
        self.queryButton.setToolTip('Query Assets Files.')
        self.queryButton.setFixedSize(30,30)
        self.queryButton.setIcon(QtGui.QIcon(QtGui.QPixmap('%s/icons/query.png' % self.base_path)))
        self.queryButton.setIconSize(QtCore.QSize(25,25))
        self.queryButton.clicked.connect(self.loading_worker.start)
        self.queryButton.setStyleSheet('''QPushButton{ border-radius:5px; background:#353535; border:none;}
                                          QPushButton:hover{ background: #252525;}
                                          QPushButton:pressed{ background: #151515;}
                                       ''')

        self.uploadButton = QtWidgets.QPushButton()
        self.uploadButton.setToolTip('Upload Assets Files In List.')
        self.uploadButton.setFixedSize(30,30)
        self.uploadButton.setIcon(QtGui.QIcon(QtGui.QPixmap('%s/icons/upload.png' % self.base_path)))
        self.uploadButton.setIconSize(QtCore.QSize(25,25))
        self.uploadButton.clicked.connect(self.upload_worker.start)
        self.uploadButton.setStyleSheet('''QPushButton{ border-radius:5px; background:#353535; border:none;}
                                          QPushButton:hover{ background: #252525;}
                                          QPushButton:pressed{ background: #151515;}
                                       ''')
        
        self.toolsLayout.addWidget(self.queryButton)
        self.toolsLayout.addWidget(self.uploadButton)
        self.mainLayout.addLayout(self.toolsLayout)
        self.mainLayout.addWidget(self.treeWidget)
        self.mainLayout.addWidget(self.busy)
    
    @QtCore.Slot(unicode, int, unicode, bool)
    def updateStatus(self, filename, column, info, typ):
        # logger.info(filename)
        items = self.treeWidget.findItems(filename, QtCore.Qt.MatchFixedString, 0)
        for item in items:
            data = item.data(column, QtCore.Qt.UserRole)
            icon_label = data['icon_label']
            info_label = data['info_label']
            info_label.setText(info)
            movie = QtGui.QMovie('%s/icons/uploading.gif' % self.base_path)
            if typ:
                icon_label.clear()
                icon_label.setPixmap(QtGui.QPixmap('%s/icons/success.png' % self.base_path))
            else:
                icon_label.clear()
                icon_label.setMovie(movie)
                movie.start()

    @QtCore.Slot(unicode, unicode, unicode, unicode, bool, bool, unicode)
    def createItem(self, asset_name, current_name, path, task, n_pub, n_ver, color):
        if n_pub and n_ver:
            itemA = QtWidgets.QTreeWidgetItem()
            itemA.setText(0, current_name)
            itemA.setText(1, task)
            itemA.setSizeHint(0, QtCore.QSize(400,25))
            itemA.setSizeHint(1, QtCore.QSize(80,25))
            itemA.setSizeHint(2, QtCore.QSize(80,25))
            itemA.setSizeHint(3, QtCore.QSize(80,25))
            itemA.setBackground(0, QtGui.QBrush(QtGui.QColor(color)))
            itemA.setBackground(1, QtGui.QBrush(QtGui.QColor(color)))
            itemA.setBackground(2, QtGui.QBrush(QtGui.QColor(color)))
            itemA.setBackground(3, QtGui.QBrush(QtGui.QColor(color)))
            itemA.setIcon(0, QtGui.QIcon(QtGui.QPixmap('%s/icons/asset.png' % self.base_path)))
            itemA.setIcon(1, QtGui.QIcon(QtGui.QPixmap('%s/icons/task.png' % self.base_path)))
            self.treeWidget.addTopLevelItem(itemA)
            self.treeWidget.setCurrentIndex(self.treeWidget.indexFromItem(itemA))

            pub_widget = QtWidgets.QWidget(self.treeWidget)
            pub_layout = QtWidgets.QHBoxLayout(pub_widget)
            pub_layout.setAlignment(QtCore.Qt.AlignLeft)
            pub_layout.setContentsMargins(0,0,0,0)
            pub_label = QtWidgets.QLabel(self.treeWidget)
            pub_label.setPixmap(QtGui.QPixmap('%s/icons/waiting.png' % self.base_path))
            pub_info_label = QtWidgets.QLabel(self.treeWidget)
            pub_info_label.setText('<font color=aliceblue>waiting</font>')
            pub_layout.addWidget(pub_label)
            pub_layout.addWidget(pub_info_label)
            itemA.setData(2, QtCore.Qt.UserRole, {'icon_label':pub_label, 'info_label':pub_info_label})

            ver_widget = QtWidgets.QWidget(self.treeWidget)
            ver_layout = QtWidgets.QHBoxLayout(ver_widget)
            ver_layout.setContentsMargins(0,0,0,0)
            ver_layout.setAlignment(QtCore.Qt.AlignLeft)
            ver_label = QtWidgets.QLabel(self.treeWidget)
            ver_label.setPixmap(QtGui.QPixmap('%s/icons/waiting.png' % self.base_path))
            ver_info_label = QtWidgets.QLabel(self.treeWidget)
            ver_info_label.setText('<font color=aliceblue>waiting</font>')
            ver_layout.addWidget(ver_label)
            ver_layout.addWidget(ver_info_label)
            itemA.setData(3, QtCore.Qt.UserRole, {'icon_label':ver_label, 'info_label':ver_info_label})

            self.treeWidget.setItemWidget(itemA, 2, pub_widget)
            self.treeWidget.setItemWidget(itemA, 3, ver_widget)

    @QtCore.Slot(bool)
    def showBusy(self, bool):
        if bool: 
            if self.busy: self.busy.show()
        else: 
            if self.busy: self.busy.hide()
         
    @QtCore.Slot(int)
    def set_other(self, value):
        if value == 0: self.treeWidget.clear()
        if value == 1: 
            if self.treeWidget.currentItem():
                self.treeWidget.currentItem().setSelected(False)
                self.treeWidget.scrollToTop()
    
    @QtCore.Slot(unicode, int)
    def set_pub_other(self, name, value):
        if value == 0:
            items = self.treeWidget.findItems(name, QtCore.Qt.MatchFixedString, 0)
            if items:
                self.treeWidget.scrollToItem(items[0], QtWidgets.QAbstractItemView.PositionAtCenter)

    def isSgPublishedFile(self, file_name, asset_name):
        asset_entity = sg.find_one('Asset', 
                                    [
                                        ['project', 'is', {'type':'Project', 'id':90}], 
                                        ['code', 'is', asset_name]
                                    ], 
                                    ['id', 'code'])
        filters = [
            ['project', 'is', {'type':'Project', 'id': 90}],
            ['code', 'is', file_name],
            ['entity', 'is', asset_entity]
        ]
        is_publish = sg.find_one('PublishedFile', filters, ['code', 'entity'])
        return is_publish
    
    def isSgVersionFile(self, file_name, asset_name):
        asset_entity = sg.find_one('Asset', 
                                    [
                                        ['project', 'is', {'type':'Project', 'id':90}], 
                                        ['code', 'is', asset_name]
                                    ], 
                                    ['id', 'code'])
        filters = [
            ['project', 'is', {'type':'Project', 'id': 90}],
            ['code', 'is', file_name],
            ['entity', 'is', asset_entity]
        ]
        is_version = sg.find_one('Version', filters, ['id'])
        return is_version

    def closeEvent(self, event):
        try: self.loading_worker.stop()
        except Exception, e: pass
        try: self.upload_worker.stop()
        except Exception, e: pass
        
class GetAssetFiles(threading.Thread):
    def __init__(self, path, trigger, trigger_run, trigger_add_item, trigger_info, trigger_direction, trigger_other, parent):
        super(GetAssetFiles, self).__init__()
        self.path = path
        self.parent = parent
        self.trigger = trigger
        self.trigger_run = trigger_run
        self.trigger_add_item = trigger_add_item
        self.trigger_info = trigger_info
        self.trigger_direction = trigger_direction
        self.trigger_other = trigger_other
    
    def run(self):
        if bool(self.parent.assets): self.parent.assets = []
        for root, dirs, files in os.walk(self.path):
            for i in files:
                if 'TEX' in root:
                    if '.jpg' in i and os.path.splitext(i)[-1] == '.jpg':
                        ttmp = root.replace('\\', '/').split('/')
                        # logger.info(ttmp)
                        if 'work' not in ttmp:
                            if 'Tex' in root:
                                asset_name = ttmp[ttmp.index('Tex') - 2]
                                base_path = os.path.join(root, i).replace('\\', '/')
                                self.parent.assets.append([asset_name, i, base_path, 'Tex']) 
                        self.trigger_info.emit(u'<font color=orange><b>File Texture Filtering...</b></font>', u'<font color=gray>%s</font>' % i, 0.00, True)
        color = ['#252525', '#303030']
        v = 0.00
        logger.warn(len(self.parent.assets))
        step = 100.00/len(self.parent.assets)
        self.trigger_direction.emit(True)
        for i in self.parent.assets:
            # logger.info(list(i))
            asset_name, current_name, path, task = i
            v += step
            logger.info(self.parent.isSgPublishedFile(current_name, asset_name))
            logger.info(self.parent.isSgVersionFile(current_name, asset_name))

            logger.info('***' * 30)
            if self.parent.isSgPublishedFile(current_name, asset_name) == None: n_pub = True
            else:n_pub = False
            if self.parent.isSgVersionFile(current_name, asset_name) == None: n_ver = True
            else: n_ver = False
            if n_pub and n_ver:
                if self.parent.upload_assets == []:self.parent.upload_assets.append([asset_name, current_name, path, task, n_pub, n_ver, 0])
                elif self.parent.upload_assets[-1][-1] == 0: self.parent.upload_assets.append([asset_name, current_name, path, task, n_pub, n_ver, 1])
                else: self.parent.upload_assets.append([asset_name, current_name, path, task, n_pub, n_ver, 0])
            self.trigger_info.emit(u'<font color=orange><b>Compare server data...</b></font>', u'<font color=gray>%s</font>' % current_name, v, False)
        if self.parent.upload_assets:
            v = 0
            step = 100.00/len(self.parent.upload_assets)
            self.trigger_direction.emit(False)
            self.trigger_other.emit(0)
            for x, cc in enumerate(self.parent.upload_assets):
                asset_name, current_name, path, task, n_pub, n_ver, color_code = cc
                v += step
                self.trigger_add_item.emit(asset_name, current_name, path, task, n_pub, n_ver, color[color_code])
                self.trigger_info.emit(u'<font color=orange><b>Create Item...</b></font>', u'<font color=gray>%s</font>' % current_name, v, False)
        self.trigger.emit(False)
        self.trigger_other.emit(1)
    
class LoadingWorker(QtCore.QThread):
    trigger = QtCore.Signal(bool)
    trigger_other = QtCore.Signal(int)
    trigger_run = QtCore.Signal(list)
    trigger_info = QtCore.Signal(unicode, unicode, float, bool)
    trigger_direction = QtCore.Signal(bool)
    trigger_add_item = QtCore.Signal(unicode, unicode, unicode, unicode, bool, bool, unicode)
    def __init__(self, path, parent): 
        super(LoadingWorker, self).__init__()
        self.path = path
        self.parent = parent
    
    def run(self):
        self.trigger.emit(True)
        self.worker = GetAssetFiles(self.path, self.trigger, self.trigger_run, self.trigger_add_item, self.trigger_info, self.trigger_direction, self.trigger_other, self.parent)
        self.worker.start()
    
    def stop(self):
        _async_raise(self.worker.ident, SystemExit)

class PublishedFiles(threading.Thread):
    def __init__(self, trigger, trigger_direction, trigger_other, trigger_info, trigger_vis_busy, assets, parent):
        super(PublishedFiles, self).__init__()
        self.assets = assets
        self.parent = parent
        self.trigger = trigger
        self.trigger_direction = trigger_direction
        self.trigger_other = trigger_other
        self.trigger_info = trigger_info
        self.trigger_vis_busy = trigger_vis_busy
        
    def run(self):
        if self.assets:
            v = 0
            step = 100.00/len(self.assets)
            self.trigger_direction.emit(True)
            self.trigger_vis_busy.emit(True)
            for asset in self.assets:
                logger.info(asset)
                asset_name, file_name, file_path, task_name, n_pub, n_ver, color_code = asset
                if n_pub and n_ver:
                    self.trigger_other.emit(file_name, 0)
                    self.trigger.emit(file_name, 2, '<font color=skyblue>uploading</font>', False)
                    project_path = os.path.dirname(self.parent.aim_project_base_path)
                    tk = sgtk.sgtk_from_path(project_path)
                    context = tk.context_from_path(file_path)
                    ctx_dict = sgtk.Context.to_dict(context)
                    asset_entity = sg.find_one('Asset', 
                                                [
                                                    ['project', 'is', {'type':'Project', 'id':90}], 
                                                    ['code', 'is', asset_name]
                                                ], 
                                                ['id', 'code'])
                    task_context = sg.find_one('Task', 
                                                [
                                                    ['project', 'is', {'type':'Project', 'id':90}], 
                                                    ['content', 'is', task_name],
                                                    ['entity', 'is', asset_entity]
                                                ], 
                                                ['id', 'content'])
                    ctx_dict['entity'] = asset_entity
                    ctx_dict['task'] = task_context
                    context = sgtk.Context.from_dict(tk, ctx_dict)
                    thumbnail_path = file_path
                    version_number = 1
                    comment = '{0} {1} texture file publish...'.format(file_name, task_name)
                    publish_file = sgtk.util.register_publish(tk, 
                                                              context, 
                                                              file_path, 
                                                              file_name.split('.')[0], 
                                                              version_number, 
                                                              comment=comment, 
                                                              thumbnail_path=thumbnail_path, 
                                                              published_file_type = 'Image'
                                                              )
                    logger.info(publish_file)
                    self.trigger.emit(file_name, 2, '<font color=green>success</font>', True)
                    self.trigger.emit(file_name, 3, '<font color=skyblue>uploading</font>', False)
                    version_data = {
                        'code':file_name,
                        'project':ctx_dict['project'],
                        'entity':ctx_dict['entity'],
                        'sg_task': ctx_dict['task'],
                        'user': ctx_dict['user'],
                        'description':'{0} {1} version create success...'.format(file_name, task_name),
                        'image': file_path
                    }
                    version = sg.create('Version', version_data)
                    uploaded = sg.upload('Version', version['id'], file_path, "sg_uploaded_movie")
                    version = {'type':'Version', 'id': version['id'], 'code': version['code']}
                    logger.info(version)
                    update_info = sg.update(publish_file['type'], publish_file['id'], {'version':version})
                    self.trigger.emit(file_name, 3, '<font color=green>success</font>', True)
                v += step
                self.trigger_info.emit(u'<font color=orange><b>Published File...</b></font>', u'<font color=gray>%s</font>' % file_name, v, False)
            self.trigger_vis_busy.emit(False)

class UploadWorker(QtCore.QThread):
    trigger = QtCore.Signal(unicode, int, unicode, bool)
    trigger_other = QtCore.Signal(unicode, int)
    trigger_vis_busy = QtCore.Signal(bool)
    trigger_direction = QtCore.Signal(bool)
    trigger_info = QtCore.Signal(unicode, unicode, float, bool)
    def __init__(self, parent):
        super(UploadWorker, self).__init__()
        self.parent = parent
        self.assets = self.parent.upload_assets

    def run(self):
        if self.assets:
            self.worker = PublishedFiles(self.trigger, self.trigger_direction, self.trigger_other, self.trigger_info, self.trigger_vis_busy, self.assets, self.parent)
            self.worker.start()
        else:
            logger.warn('Not assets files.')
    
    def stop(self):
        _async_raise(self.worker.ident, SystemExit)
