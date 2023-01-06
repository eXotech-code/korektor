#!/usr/bin/env python3

"""
Program służący do klonowania wybranego
fragmentu zdjęcia i wklejania go w inne
miejsce na tym samym zdjęciu. Zapewnia
możliwość podglądu wyniku operacji
w czasie rzeczywistym.
"""

from dataclasses import dataclass
import numbers
import wx
# import wx.lib.inspection


# pylint: disable=too-few-public-methods
class Colours:
    """
    Ta klasa zawiera predefiniowane
    kolory używane w interfejsie programu.
    Jeżeli na komputerze włączony jest tryb
    ciemny, zwracane kolory są dopasowane
    do tegoż środowiska kolorystycznego.
    """

    COLOURS = {
        "background": "#fff",
        "text": "#161616",
        "textSecondary": "#808080",
        "buttonBlueText": "#fff",
        "uiBackground": "#F4F4F4",
        "buttonBlue": "#0F62FE"
    }

    DARK_COLOURS = {
        "background": "#161616",
        "text": "#f4f4f4",
        "textSecondary": "#808080",
        "buttonBlueText": "#fff",
        "uiBackground": "#262626",
        "buttonBlue": "#0F62FE"
    }

    def __adapted_colours__(self):
        if wx.SystemSettings.GetAppearance().IsDark():
            return self.DARK_COLOURS
        return self.COLOURS

    def get(self, colour_name):
        """
        Zwraca kolor odpowiadający jego nazwie
        pasujący pod paletę systemową.
        """
        return self.__adapted_colours__().get(colour_name)


class OperandError(TypeError):
    """
    Błąd użycia złego typu danych podczas
    przeprowadzania operacji na obiektach
    typu Point
    """

    def __init__(self, operation, operand):
        operand_type = type(operand).__name__
        message = f"Invalid operand types for {operation}: Point and {operand_type}."
        super().__init__(message)


class Point:
    """
    Reprezentuje punkt na płasczyźnie.
    """

    def __init__(self, x_or_point, y=None):
        if y is None:
            self.x = x_or_point[0]
            self.y = x_or_point[1]
        else:
            self.x = x_or_point
            self.y = y

    def __add__(self, right):
        if isinstance(right, Point):
            return Point(self.x + right.x, self.y + right.y)
        if isinstance(right, numbers.Number):
            # To jest suma skalarna.
            return Point(self.x + right, self.y + right)
        raise OperandError("+", right)

    def __sub__(self, right):
        if isinstance(right, Point):
            return Point(self.x - right.x, self.y - right.y)
        if isinstance(right, numbers.Number):
            # To jest suma skalarna.
            return Point(self.x - right, self.y - right)
        raise OperandError("-", right)

    def __mul__(self, right):
        if isinstance(right, Point):
            return Point(self.x * right.x, self.y * right.y)
        if isinstance(right, numbers.Number):
            return Point(self.x * right, self.y * right)
        raise OperandError("*", right)

    def __truediv__(self, right):
        if isinstance(right, Point):
            return Point(self.x / right.x, self.y / right.y)
        if isinstance(right, numbers.Number):
            return Point(self.x / right, self.y / right)
        raise OperandError("/", right)

    def __floordiv__(self, right):
        if isinstance(right, Point):
            return Point(self.x // right.x, self.y // right.y)
        if isinstance(right, numbers.Number):
            return Point(self.x // right, self.y // right)
        raise OperandError("//", right)

    def round(self):
        """
        Zwraca nowy punkt, którego koordynaty są całkowitoliczbowe.
        """
        return Point(round(self.x), round(self.y))

    def ratio(self):
        """
        Zwraca stosunek długości do wysokości.
        Metoda przydatna do obliczeń proporcji zdjęcia.
        """
        return self.x / self.y


class SelectedArea:
    """
    Reprezentuje obszar zaznaczony na zdjęciu przez użytkownika.
    """

    def __init__(self, top_left=None):
        self.selected_area = [top_left, None]

    def __imul__(self, right):
        for i in range(2):
            self.selected_area[i] = self.selected_area[i] * right
        return self

    def close(self, bottom_right):
        """
        Zamknij zaznaczony prostokątny obszar
        poprzez dodanie koordynatów prawego-dolnego
        rogu zaznaczenia.
        """
        self.selected_area[1] = bottom_right

    def is_selected(self):
        """
        Obszar jest uważany za zamknięty, jeżeli
        posiada lewy-górny róg oraz prawy-dolny.
        """
        return self.selected_area[1] is not None

    def get_width_height(self):
        """
        Zwraca szerokość i wysokość zaznaczenia.
        """
        if not self.is_selected:
            raise ValueError("Not possible to get width and height of null selection.")
        return self.selected_area[1] - self.selected_area[0]

    def __image_to_window__(self, coord, offset):
        """
        Konwertuje koordynaty z przestrzeni zdjęcia na przestrzeń
        okna.
        """
        return coord + offset

    def get_top_left_translated(self, offset):
        """
        Zwraca koordynaty lewego-górnego rogu zaznaczenia
        przesunięte o offset.
        """
        return self.__image_to_window__(self.selected_area[0], offset)


@dataclass
class ScalingReturnVal:
    """
    Klasa reprezentująca zestaw wartości uzyskanych
    w wyniku skalowania pewnego prostokątnego obiektu.
    """
    scale: Point
    old_width: float
    new_width: float
    old_height: float
    new_height: float

    def factor(self):
        """
        Ilukrotna zmiana wielkości obiektu nastąpiła?
        """
        return Point(self.new_width / self.old_width, self.new_height / self.old_height)


class Image(wx.Image):
    """
    Zdjęcie, które wspiera bezstratną zmianę rozmiaru oraz
    kopiowanie jego fragmentu.
    """

    def __init__(self, image_path):
        super().__init__(image_path, wx.BITMAP_TYPE_PNG)
        self.scale = Point(self.GetWidth(), self.GetHeight())

    def update_scale(self, new_scale):
        """
        Podmienia obecną skalę zdjęcia na nową.
        """
        self.scale = new_scale

    def get_bitmap(self, dc):
        """
        Zwraca bitmapę kompatybilną z obecnyn Device Context.
        """
        scale = self.scale.round()
        img = self.Scale(scale.x, scale.y)
        return wx.Bitmap(img, dc)


class ImageView(wx.Panel):
    """
    Widok edycyjny zdjęcia z możliwością zaznaczenia fragmentu zdjęcia
    i wklejenia zaznaczonego fragmentu w wybrane miejsce.
    """

    def __init__(self, image, colours, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = Image(image)
        self.colours = colours
        self.selected_area = SelectedArea()
        self.selection_rescale_lock = True
        self.window_dc = None
        self.Bind(wx.EVT_PAINT, self.__paint__)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_mouse_down__)
        self.Bind(wx.EVT_MOTION, self.__on_drag__)
        self.Bind(wx.EVT_SIZE, self.__on_resize__)

    # Returns scaled values for width and height.
    def __scale_to_fit__(self, container_size, element_size):
        """
        Skaluje prostokątny obiekt, tak aby zajmował jak
        najwięlszą pojemność swojego kontenera bez zmiany
        jego formatu.
        """
        container_ratio = container_size.ratio()
        element_ratio = element_size.ratio()

        if element_ratio <= container_ratio:
            new_height = container_size.y
            new_width = new_height * element_ratio
        elif element_ratio > container_ratio:
            new_width = container_size.x
            new_height = new_width / element_ratio
        return ScalingReturnVal(
                Point(new_width, new_height),
                element_size.x,
                new_width,
                element_size.y,
                new_height
        )

    def __get_center__(self):
        """
        Zwraca koordynaty środka tego okna.
        """
        return Point([int(x / 2) for x in self.GetSize()])

    def __get_top_left__(self):
        """
        Zwraca koordynaty lewego-górnego rogu zdjęcia
        na podstawie środka okna i wielkości zdjęcia.
        """
        center = self.__get_center__()
        return center - self.img.scale / 2

    def __new_size__(self):
        """
        Jeżeli okno jest widoczne na ekranie
        skaluje zdjęcie, tak aby wypełniało
        jak największą jego powierzchnię.
        Dokonuje również zmiany rozmiaru obszaru
        zaznaczonego na zdjęciu, jeżeli takowy istnieje.
        """
        parent = self.GetParent()
        if parent.IsShownOnScreen():
            container_size = Point(self.GetSize())
            scaling = self.__scale_to_fit__(container_size, self.img.scale)
            self.img.update_scale(scaling.scale)
            if self.selected_area.is_selected() and not self.selection_rescale_lock:
                self.selected_area *= scaling.factor()

    def __draw_image__(self, dc):
        self.__new_size__()
        bmp = self.img.get_bitmap(dc)
        top_left = self.__get_top_left__().round()
        dc.DrawBitmap(bmp, top_left.x, top_left.y)

    def __draw_selection__(self, dc):
        # Nie próbuj narysować obszaru zaznaczonego jeżeli
        # on nie istnieje (trochę oczywiste xD).
        if not self.selected_area.is_selected():
            return
        pen = wx.Pen(self.colours.get("textSecondary"), width=2, style=wx.PENSTYLE_LONG_DASH)
        brush = wx.Brush(wx.Colour(0, 0, 0, wx.ALPHA_TRANSPARENT))
        dc.SetPen(pen)
        dc.SetBrush(brush)
        offset = self.__get_top_left__()
        top_left = self.selected_area.get_top_left_translated(offset)
        top_left = top_left.round()
        width_height = self.selected_area.get_width_height()
        width_height = width_height.round()
        dc.DrawRectangle(top_left.x, top_left.y, width_height.x, width_height.y)

    def __paint__(self, _):
        dc = wx.GCDC(wx.PaintDC(self))
        self.__draw_image__(dc)
        self.__draw_selection__(dc)

    def __get_window_dc__(self):
        if self.window_dc is None:
            self.window_dc = wx.WindowDC(self)
        return self.window_dc

    def __on_mouse_down__(self, event):
        pos = Point(event.GetLogicalPosition(self.__get_window_dc__()).Get())
        self.selected_area = SelectedArea(pos - self.__get_top_left__())
        self.Refresh()

    def __on_drag__(self, event):
        if event.Dragging():
            self.selection_rescale_lock = True
            pos = Point(event.GetLogicalPosition(self.__get_window_dc__()).Get())
            self.selected_area.close(pos - self.__get_top_left__())
            self.Refresh()

    def __on_resize__(self, _):
        self.selection_rescale_lock = False


class MainFrame(wx.Frame):
    """
    Główne okno interfejsu graficznego.
    """

    def __init__(self, colours):
        super().__init__(None, title="korektor", size=(924, 512))
        self.SetBackgroundColour(colours.get("background"))
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.image_view = ImageView("lun.png", colours, self)
        self.sizer.Add(self.image_view, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self.sizer)
        self.__make_menu_bar__()
        self.Show()

    def __make_menu_bar__(self):
        # Menu bar with one File menu opening an info box about the app
        # and a button to exit the app.
        # On MacOS the Quit and About buttons are automatically moved
        # to the app main menu.
        file_menu = wx.Menu()
        ex = file_menu.Append(wx.ID_EXIT, "Quit", "Quit application.")
        about = file_menu.Append(wx.ID_ABOUT, "About korektor", "Show about info.")
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        self.SetMenuBar(menu_bar)

        # Binding menu buttons to actions.
        self.Bind(wx.EVT_MENU, self.__on_exit__, ex)
        self.Bind(wx.EVT_MENU, self.__on_about__, about)

    def __on_exit__(self, _):
        self.Close(True)

    def __on_about__(self, _):
        wx.MessageBox("korektor\n Copyright (C) Jakub Piśkiewicz 2022", "About korektor")


class Korektor(wx.App):
    """
    Obiekt tej klasy uruchamia interfejs graficzny gdy powstaje.
    """

    NAME = "korektor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetAppName(self.NAME)
        self.SetAppDisplayName(self.NAME)
        self.SetTopWindow(MainFrame(Colours()))
        self.MainLoop()


if __name__ == '__main__':
    Korektor()
    # wx.lib.inspection.InspectionTool().Show()
