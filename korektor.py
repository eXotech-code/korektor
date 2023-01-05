#!/usr/bin/env python3

import wx
import wx.lib.inspection

class Colour():
    def __init__(self, colourName):
        colours = {
            "background": "#fff",
            "text": "#161616",
            "textSecondary": "#808080",
            "buttonBlueText": "#fff",
            "uiBackground": "#F4F4F4",
            "buttonBlue": "#0F62FE"
        }

        if wx.SystemSettings.GetAppearance().IsDark():
            colours = {
                "background": "#161616",
                "text": "#f4f4f4",
                "textSecondary": "#808080",
                "buttonBlueText": "#fff",
                "uiBackground": "#262626",
                "buttonBlue": "#0F62FE"
            }

        self.c = colours.get(colourName)

class ScalingReturnVal:
    def __init__(self, scale, oldWidth, newWidth, oldHeight, newHeight):
        self.scale = scale
        self.scalingRatioX = newWidth / oldWidth
        self.scalingRatioY = newHeight / oldHeight

class ImageView(wx.Panel):
    def __init__(self, image, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = wx.Image(image, wx.BITMAP_TYPE_PNG)
        self.imgScale = [self.img.GetWidth(), self.img.GetHeight()]
        self.selectedArea = [None, None] # In image's coordinate system (0, 0) = top-left corner.
        self.selectionRescaleLock = True
        self.Bind(wx.EVT_PAINT, self.__paint__)
        self.Bind(wx.EVT_LEFT_DOWN, self.__onMouseDown__)
        self.Bind(wx.EVT_MOTION, self.__onDrag__)
        self.Bind(wx.EVT_SIZE, self.__onResize__)

    # Returns scaled values for width and height.
    def __scaleToFit__(self, containerSize, elementSize):
        cWidth, cHeight = containerSize
        eWidth, eHeight = elementSize
        containerRatio = cWidth / cHeight
        elementRatio = eWidth / eHeight
        if elementRatio <= containerRatio:
            newHeight = cHeight
            newWidth = newHeight * elementRatio
        elif elementRatio > containerRatio:
            newWidth = cWidth
            newHeight = newWidth / elementRatio
        return ScalingReturnVal((newWidth, newHeight), eWidth, newWidth, eHeight, newHeight)

    # Returns coords of center of this frame.
    def __getCenter__(self):
        return [int(x / 2) for x in self.GetSize()]

    # Returns where top-left corner of image should be
    # based on the center of frame and image size.
    def __getTopLeft__(self):
        center = self.__getCenter__()
        res = []
        for i in range(len(center)):
            res.append(center[i] - self.imgScale[i] / 2)
        return res

    def __rescaleSelection__(self, scale):
        if self.selectionRescaleLock:
            return
        self.selectedArea[0] = (self.selectedArea[0][0] * scale.scalingRatioX, self.selectedArea[0][1] * scale.scalingRatioY)
        self.selectedArea[1] = (self.selectedArea[1][0] * scale.scalingRatioX, self.selectedArea[1][1] * scale.scalingRatioY)

    # Returns a difference of each coordinate values
    # between two points.
    def __calcXYDiff__(self, val1, val2):
        return [val1[i] - val2[i] for i in range(2)]

    # Resizes image alng with it's selection area if it exists.
    def __newSize__(self):
        parent = self.GetParent()
        if parent.IsShownOnScreen():
            containerSize = self.GetSize()
            rescaled = self.__scaleToFit__(containerSize, self.imgScale)
            self.imgScale = rescaled.scale
            if self.selectedArea[1]:
                self.__rescaleSelection__(rescaled)

    # Returns scaled image to new size.
    def __resize__(self):
        self.__newSize__()
        imgScale = [round(x) for x in self.imgScale]
        return self.img.Scale(*imgScale)

    def __drawImage__(self, dc):
        img = self.__resize__()
        if img:
            bmp = wx.Bitmap(img, dc)
            topLeft = [round(x) for x in self.__getTopLeft__()]
            dc.DrawBitmap(bmp, *topLeft)

    # Translates given coordinate to window coordinate system.
    # (adds vertical / horizontal shift of the image)
    def __translateToWindowCS__(self, coord):
        topLeft = self.__getTopLeft__()
        return [coord[i] + topLeft[i] for i in range(2)]

    def __getSelectedWidthHeight__(self, area):
        if not self.selectedArea[1]:
            raise ValueError("Not possible to get width and height of null selection.")
        return self.__calcXYDiff__(area[1], area[0])

    def __nestedFloatArrayToInt__(self, arr):
        return [[round(x) for x in ls] for ls in arr]

    def __drawSelection__(self, dc):
        # Don't try to draw a selection if nothing was selected.
        if not self.selectedArea[1]: return
        pen = wx.Pen(Colour("textSecondary").c, width=2, style=wx.PENSTYLE_LONG_DASH)
        brush = wx.Brush(wx.Colour(0, 0, 0, wx.ALPHA_TRANSPARENT))
        dc.SetPen(pen)
        dc.SetBrush(brush)
        translatedArea = [self.__translateToWindowCS__(x) for x in self.selectedArea]
        translatedArea = self.__nestedFloatArrayToInt__(translatedArea)
        dc.DrawRectangle(*translatedArea[0], *self.__getSelectedWidthHeight__(translatedArea))

    def __paint__(self, event):
        dc = wx.GCDC(wx.PaintDC(self))
        self.__drawImage__(dc)
        self.__drawSelection__(dc)

    def __getWindowDC__(self):
        if not hasattr(self, "windowDC"):
            self.windowDC = wx.WindowDC(self)
        return self.windowDC

    def __onMouseDown__(self, event):
        pos = event.GetLogicalPosition(self.__getWindowDC__()).Get()
        self.selectedArea = [[pos[i] - self.__getTopLeft__()[i] for i in range(2)], None] # Start the square.
        self.Refresh()

    def __onDrag__(self, event):
        if event.Dragging():
            self.selectionRescaleLock = True
            pos = event.GetLogicalPosition(self.__getWindowDC__()).Get()
            self.selectedArea[1] = [pos[i] - self.__getTopLeft__()[i] for i in range(2)] # Close the square.
            self.Refresh()

    def __onResize__(self, event):
        self.selectionRescaleLock = False

class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(None, title="korektor", size=(924, 512))
        self.SetBackgroundColour(Colour("background").c)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.__makeImageView__("lun.png")
        self.SetSizer(self.sizer)
        self.Show()

    def __makeImageView__(self, imagePath):
        self.imageView = ImageView(imagePath, self)
        self.sizer.Add(self.imageView, proportion=1, flag=wx.EXPAND)

if __name__ == '__main__':
    app = wx.App()
    frm = MainFrame()
    app.SetTopWindow(frm)
    # wx.lib.inspection.InspectionTool().Show()
    app.MainLoop()
