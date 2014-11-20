#!/usr/bin/python
# -*- coding: utf-8 -*-
#-----------------------------------------------------------------------#
#                                                                       #
# This file is part of the Horus Project                                #
#                                                                       #
# Copyright (C) 2014 Mundo Reader S.L.                                  #
#                                                                       #
# Date: June & November 2014                                            #
# Author: Jesús Arroyo Torrens <jesus.arroyo@bq.com>                    #
#                                                                       #
# This program is free software: you can redistribute it and/or modify  #
# it under the terms of the GNU General Public License as published by  #
# the Free Software Foundation, either version 2 of the License, or     #
# (at your option) any later version.                                   #
#                                                                       #
# This program is distributed in the hope that it will be useful,       #
# but WITHOUT ANY WARRANTY; without even the implied warranty of        #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the          #
# GNU General Public License for more details.                          #
#                                                                       #
# You should have received a copy of the GNU General Public License     #
# along with this program. If not, see <http://www.gnu.org/licenses/>.  #
#                                                                       #
#-----------------------------------------------------------------------#

__author__ = "Jesús Arroyo Torrens <jesus.arroyo@bq.com>"
__license__ = "GNU General Public License v2 http://www.gnu.org/licenses/gpl.html"

import wx._core

import horus.util.error as Error
from horus.util import resources, profile

from horus.gui.util.imageView import VideoView
from horus.gui.util.sceneView import SceneView
from horus.gui.util.customPanels import ExpandableControl

from horus.gui.workbench.workbench import WorkbenchConnection
from horus.gui.workbench.scanning.panels import ScanParameters, ImageAcquisition, \
												ImageSegmentation, PointCloudGeneration

from horus.engine.scan import SimpleScan, TextureScan

class ScanningWorkbench(WorkbenchConnection):

	def __init__(self, parent):
		WorkbenchConnection.__init__(self, parent)

		self.playing = False
		self.showVideoViews = False

		self.simpleScan = SimpleScan.Instance()
		self.textureScan = TextureScan.Instance()

		self.currentScan = self.simpleScan

		self.load()

		self.pointCloudTimer = wx.Timer(self)
		self.Bind(wx.EVT_TIMER, self.onPointCloudTimer, self.pointCloudTimer)

	def load(self):
		#-- Toolbar Configuration
		self.playTool   = self.toolbar.AddLabelTool(wx.NewId(), _("Play"), wx.Bitmap(resources.getPathForImage("play.png")), shortHelp=_("Play"))
		self.stopTool   = self.toolbar.AddLabelTool(wx.NewId(), _("Stop"), wx.Bitmap(resources.getPathForImage("stop.png")), shortHelp=_("Stop"))
		self.pauseTool  = self.toolbar.AddLabelTool(wx.NewId(), _("Pause"), wx.Bitmap(resources.getPathForImage("pause.png")), shortHelp=_("Pause"))
		self.resumeTool = self.toolbar.AddLabelTool(wx.NewId(), _("Resume"), wx.Bitmap(resources.getPathForImage("resume.png")), shortHelp=_("Resume"))
		self.undoTool   = self.toolbar.AddLabelTool(wx.NewId(), _("Undo"), wx.Bitmap(resources.getPathForImage("undo.png")), shortHelp=_("Undo"))
		self.deleteTool = self.toolbar.AddLabelTool(wx.NewId(), _("Delete"), wx.Bitmap(resources.getPathForImage("delete.png")), shortHelp=_("Clear"))
		self.toolbar.Realize()

		#-- Disable Toolbar Items
		self.enableLabelTool(self.playTool  , False)
		self.enableLabelTool(self.stopTool  , False)
		self.enableLabelTool(self.pauseTool , False)
		self.enableLabelTool(self.resumeTool, False)
		self.enableLabelTool(self.undoTool  , False)
		self.enableLabelTool(self.deleteTool, True)

		#-- Bind Toolbar Items
		self.Bind(wx.EVT_TOOL, self.onPlayToolClicked  , self.playTool)
		self.Bind(wx.EVT_TOOL, self.onStopToolClicked  , self.stopTool)
		self.Bind(wx.EVT_TOOL, self.onPauseToolClicked , self.pauseTool)
		self.Bind(wx.EVT_TOOL, self.onResumeToolClicked, self.resumeTool)
		self.Bind(wx.EVT_TOOL, self.onUndoToolClicked  , self.undoTool)
		self.Bind(wx.EVT_TOOL, self.onDeleteToolClicked, self.deleteTool)

		self.scrollPanel = wx.lib.scrolledpanel.ScrolledPanel(self._panel, size=(290,-1))
		self.scrollPanel.SetupScrolling(scroll_x=False, scrollIntoView=False)
		self.scrollPanel.SetAutoLayout(1)

		self.controls = ExpandableControl(self.scrollPanel)

		self.controls.addPanel('scan_parameters', ScanParameters(self.controls))
		self.controls.addPanel('image_acquisition', ImageAcquisition(self.controls))
		self.controls.addPanel('image_segmentation', ImageSegmentation(self.controls))
		self.controls.addPanel('point_cloud_generation', PointCloudGeneration(self.controls))

		self.controls.setUndoCallbacks(self.appendToUndo, self.releaseUndo)

		self.splitterWindow = wx.SplitterWindow(self._panel)

		self.videoView = VideoView(self.splitterWindow, self.getFrame, 200)
		self.sceneView = SceneView(self.splitterWindow)
		self.videoView.SetBackgroundColour(wx.BLACK)
		self.sceneView.SetBackgroundColour(wx.BLACK)

		self.splitterWindow.SplitVertically(self.videoView, self.sceneView)
		self.splitterWindow.SetMinimumPaneSize(200)

		#-- Layout
		vsbox = wx.BoxSizer(wx.VERTICAL)
		vsbox.Add(self.controls, 0, wx.ALL|wx.EXPAND, 0)
		self.scrollPanel.SetSizer(vsbox)
		vsbox.Fit(self.scrollPanel)

		self.addToPanel(self.scrollPanel, 0)
		self.addToPanel(self.splitterWindow, 1)

		#- Video View Selector
		self.buttonShowVideoViews = wx.BitmapButton(self.videoView, wx.NewId(), wx.Bitmap(resources.getPathForImage("views.png"), wx.BITMAP_TYPE_ANY), (10,10))
		self.buttonLaser  = wx.RadioButton(self.videoView, wx.NewId(), _("Laser"), pos=(10,15+40))
		self.buttonGray = wx.RadioButton(self.videoView, wx.NewId(), _("Gray"), pos=(10,15+80))
		self.buttonLine  = wx.RadioButton(self.videoView, wx.NewId(), _("Line"), pos=(10,15+120))
		self.buttonColor  = wx.RadioButton(self.videoView, wx.NewId(), _("Color"), pos=(10,15+160))

		self.buttonShowVideoViews.Hide()
		self.buttonLaser.Hide()
		self.buttonGray.Hide()
		self.buttonLine.Hide()
		self.buttonColor.Hide()

		selectedView = {'laser' : self.buttonLaser,
						'gray'  : self.buttonGray,
						'line'  : self.buttonLine,
						'color' : self.buttonColor}

		selectedView[profile.getProfileSetting('img_type')].SetValue(True)

		self.buttonLaser.SetForegroundColour(wx.WHITE)
		self.buttonGray.SetForegroundColour(wx.WHITE)
		self.buttonLine.SetForegroundColour(wx.WHITE)
		self.buttonColor.SetForegroundColour(wx.WHITE)

		self.buttonLaser.SetBackgroundColour(wx.BLACK)
		self.buttonGray.SetBackgroundColour(wx.BLACK)
		self.buttonLine.SetBackgroundColour(wx.BLACK)
		self.buttonColor.SetBackgroundColour(wx.BLACK)

		self.Bind(wx.EVT_BUTTON, self.onShowVideoViews, self.buttonShowVideoViews)
		self.Bind(wx.EVT_RADIOBUTTON, self.onSelectVideoView, self.buttonLaser)
		self.Bind(wx.EVT_RADIOBUTTON, self.onSelectVideoView, self.buttonGray)
		self.Bind(wx.EVT_RADIOBUTTON, self.onSelectVideoView, self.buttonLine)
		self.Bind(wx.EVT_RADIOBUTTON, self.onSelectVideoView, self.buttonColor)

		self.Layout()

		#-- Undo
		self.undoObjects = []

	def initialize(self):
		self.controls.initialize()

	def onShow(self, event):
		if event.GetShow():
			self.updateStatus(self.currentScan.driver.isConnected)
			self.pointCloudTimer.Stop()
			self.pointCloudTimer.Start(milliseconds=50)
			self.videoView.play()
		else:
			try:
				self.pointCloudTimer.Stop()
				self.videoView.stop()
			except:
				pass

	def onShowVideoViews(self, event):
		self.showVideoViews = not self.showVideoViews
		if self.showVideoViews:
			self.buttonLaser.Show()
			self.buttonGray.Show()
			self.buttonLine.Show()
			self.buttonColor.Show()
		else:
			self.buttonLaser.Hide()
			self.buttonGray.Hide()
			self.buttonLine.Hide()
			self.buttonColor.Hide()

	def onSelectVideoView(self, event):
		selectedView = {self.buttonLaser.GetId() : 'laser',
						self.buttonGray.GetId()  : 'gray',
						self.buttonLine.GetId()  : 'line',
						self.buttonColor.GetId() : 'color'}.get(event.GetId())

		self.currentScan.setImageType(selectedView)
		profile.putProfileSetting('img_type', selectedView)

	def getFrame(self):
		return self.currentScan.getImage()

	def onPointCloudTimer(self, event):
		pointCloud = self.currentScan.getPointCloudIncrement()
		if pointCloud is not None:
			if pointCloud[0] is not None and pointCloud[1] is not None:
				if len(pointCloud[0]) > 0:
					self.sceneView.appendPointCloud(pointCloud[0], pointCloud[1])

	def onPlayToolClicked(self, event):
		result = True
		if self.sceneView._object is not None:
			dlg = wx.MessageDialog(self, _("Your current model will be erased.\nDo you really want to do it?"), _("Clear Point Cloud"), wx.YES_NO | wx.ICON_QUESTION)
			result = dlg.ShowModal() == wx.ID_YES
			dlg.Destroy()
		if result:
			self.currentScan.setCallbacks(self.beforeScan, None, lambda r: wx.CallAfter(self.afterScan,r))
			self.currentScan.start()

	def beforeScan(self):
		self.buttonShowVideoViews.Show()
		self.enableLabelTool(self.disconnectTool, False)
		self.enableLabelTool(self.playTool, False)
		self.enableLabelTool(self.stopTool, True)
		self.enableLabelTool(self.pauseTool , True)
		self.enableLabelTool(self.resumeTool, False)
		self.enableLabelTool(self.deleteTool, False)
		self.sceneView.createDefaultObject()
		self.videoView.play()
		self.combo.Disable()
		self.pointCloudTimer.Start(milliseconds=50)

	def afterScan(self, response):
		ret, result = response
		if ret:
			dlg = wx.MessageDialog(self, _("Scanning has finished. If you want to save your point cloud go to File > Save Model"), _("Scanning finished!"), wx.OK|wx.ICON_INFORMATION)
			dlg.ShowModal()
			dlg.Destroy()
			self.onScanFinished()

	def onStopToolClicked(self, event):
		paused = self.currentScan.inactive
		self.currentScan.pause()
		dlg = wx.MessageDialog(self, _("Your current scanning will be stopped.\nDo you really want to do it?"), _("Stop Scanning"), wx.YES_NO | wx.ICON_QUESTION)
		result = dlg.ShowModal() == wx.ID_YES
		dlg.Destroy()

		if result:
			self.currentScan.stop()
			self.onScanFinished()
		else:
			if not paused:
				self.currentScan.resume()

	def onScanFinished(self):
		self.enableLabelTool(self.disconnectTool, True)
		self.enableLabelTool(self.playTool, True)
		self.enableLabelTool(self.stopTool, False)
		self.enableLabelTool(self.pauseTool , False)
		self.enableLabelTool(self.resumeTool, False)
		self.enableLabelTool(self.deleteTool, True)
		self.combo.Enable()
		#self.buttonShowVideoViews.Hide()
		#self.buttonLaser.Hide()
		#self.buttonGray.Hide()
		#self.buttonLine.Hide()
		#self.buttonColor.Hide()
		#self.videoView.stop()
		self.pointCloudTimer.Stop()

	def onPauseToolClicked(self, event):
		self.enableLabelTool(self.pauseTool , False)
		self.enableLabelTool(self.resumeTool, True)
		self.enableLabelTool(self.deleteTool, False)
		
		self.currentScan.pause()
		self.pointCloudTimer.Stop()
		#self.videoView.pause()

	def onResumeToolClicked(self, event):
		self.enableLabelTool(self.pauseTool , True)
		self.enableLabelTool(self.resumeTool, False)
		self.enableLabelTool(self.deleteTool, False)
		
		self.currentScan.resume()
		self.pointCloudTimer.Start(milliseconds=50)
		#self.videoView.play()

	def onDeleteToolClicked(self, event):
		if self.sceneView._object is not None:
			dlg = wx.MessageDialog(self, _("Your current model will be erased.\nDo you really want to do it?"), _("Clear Point Cloud"), wx.YES_NO | wx.ICON_QUESTION)
			result = dlg.ShowModal() == wx.ID_YES
			dlg.Destroy()
			if result:
				self.sceneView._clearScene()

	def onUndoToolClicked(self, event):
		self.enableLabelTool(self.undoTool, self.undo())

	def appendToUndo(self, _object):
		self.undoObjects.append(_object)

	def releaseUndo(self):
		self.enableLabelTool(self.undoTool, True)

	def undo(self):
		if len(self.undoObjects) > 0:
			objectToUndo = self.undoObjects.pop()
			objectToUndo.undo()
		return len(self.undoObjects) > 0

	def updateToolbarStatus(self, status):
		if status:
			self.enableLabelTool(self.playTool  , True)
			self.enableLabelTool(self.stopTool  , False)
			self.enableLabelTool(self.pauseTool , False)
			self.enableLabelTool(self.resumeTool, False)
			self.enableLabelTool(self.deleteTool, True)
			self.controls.enableContent()
			self.buttonShowVideoViews.Show()
		else:
			self.enableLabelTool(self.playTool  , False)
			self.enableLabelTool(self.stopTool  , False)
			self.enableLabelTool(self.pauseTool , False)
			self.enableLabelTool(self.resumeTool, False)
			self.enableLabelTool(self.deleteTool, True)
			self.controls.disableContent()
			self.buttonShowVideoViews.Hide()
			self.buttonLaser.Hide()
			self.buttonGray.Hide()
			self.buttonLine.Hide()
			self.buttonColor.Hide()

	def updateProfileToAllControls(self):
		self.controls.updateProfile()