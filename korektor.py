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
        "border": "#808080",
    }

    DARK_COLOURS = {
        "background": "#161616",
        "border": "#f0f0f0",
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
    typu Point.
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

    def __str__(self):
        return f"Point(x={self.x}, y={self.y})"

    def __eq__(self, right):
        return self.x == right.x and self.y == right.y

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
        if isinstance(right, Point):
            for i in range(2):
                self.selected_area[i] = self.selected_area[i] * right
            return self
        raise OperandError("*=", right)

    def __truediv__(self, right):
        if isinstance(right, Point):
            res = SelectedArea(self.selected_area[0] / right)
            res.close(self.selected_area[1] / right)
            return res
        raise OperandError("/", right)

    def __has_proper_rect__(self):
        return self.selected_area[0].x < self.selected_area[1].x

    def __sort_short__(self, vals):
        """
        Sortowanie list dwuelementowych.
        """
        if vals[0] > vals[1]:
            temp = vals[0]
            vals[0] = vals[1]
            vals[1] = temp
        return vals

    def __sort_coords__(self, coord1, coord2):
        xs = [coord1.x, coord2.x]
        ys = [coord1.y, coord2.y]
        xs = self.__sort_short__(xs)
        ys = self.__sort_short__(ys)
        return xs, ys

    def __convert_coords__(self):
        """
        Zamiana zapisanej formy zaznaczenia na
        format [lewy_górny_róg, prawy_dolny_róg].
        """
        if not self.__has_proper_rect__():
            increasing = self.__sort_coords__(self.selected_area[0], self.selected_area[1])
            top_left = Point(increasing[0][0], increasing[1][0])
            bottom_right = Point(increasing[0][1], increasing[1][1])
            return [top_left, bottom_right]
        return self.selected_area

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
        posiada dwa rogi.
        """
        return self.selected_area[1] is not None

    def __get_dimensions__(self, rect):
        """
        Zwraca szerokość i wysokość prostokąta o formacie
        [lewy_górny_róg, prawy_dolny_róg].
        """
        if not self.is_selected():
            raise ValueError("Not possible to get width and height of null selection.")
        return rect[1] - rect[0]

    def get_width_height(self):
        """
        Zwraca wymiary zaznaczenia.
        """
        return self.__get_dimensions__(self.selected_area)

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

    def to_wx_rect(self):
        """
        Zamienia prostokątny obszar zaznaczenia zapisany w obiekcie tej klasy na
        obiekt klasy wx.Rect aby ułatwić kopiowanie zaznaczonego obszaru zdjęcia.
        """
        if self.is_selected():
            converted = self.__convert_coords__()
            top_left = converted[0].round()
            width_height = self.__get_dimensions__(converted).round()
            return wx.Rect(top_left.x, top_left.y, width_height.x, width_height.y)
        raise AttributeError("Not possible to convert null selection to wx.Rect object.")


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


class FileDialog(wx.FileDialog):
    """
    Klasa dziedzicząca z wx.FileDialog ułatwiająca tworzenie menu wyboru
    nazwy pliku do otwarcia / zapisania.
    """

    def __init__(self, parent, action):
        if action == "open":
            style = wx.FD_OPEN|wx.FD_FILE_MUST_EXIST
            name = "Otwórz obraz"
        else:
            style = wx.FD_SAVE
            name = "Zapisz obraz"
        super().__init__(parent, name, wildcard="*.png", style=style)

    def get_filename(self):
        """
        Zwraca nazwę pliku wybraną przez użytkownika.
        """
        if self.ShowModal() == wx.ID_CANCEL:
            return None
        return self.GetPath()


class Image(wx.Image):
    """
    Zdjęcie, które wspiera bezstratną zmianę rozmiaru oraz
    kopiowanie jego fragmentu.
    """

    def __init__(self, image):
        if isinstance(image, wx.Image):
            # Jeżeli przekazano obiekt typu wx.Image
            # do konstruktora, zainicjalizuj klasę bazową, tak aby
            # stała się kopią tego obiektu.
            super().__init__(image) # Użycie konstruktora kopiującego wx.Object
        else:
            super().__init__(image, wx.BITMAP_TYPE_PNG)
        self.scale = Point(self.GetWidth(), self.GetHeight())
        # Kopia zdjęcia ze skalą pasującą do obecnej wielkości okna
        # zapisana jako bitmapa. Używana jest, gdy wynik funkcji
        # self.get_scaled() potrzebny jest więcej niż raz.
        self.bitmap_cache = None

    def update_scale(self, new_scale):
        """
        Podmienia obecną skalę zdjęcia na nową.
        """
        self.scale = new_scale

    def get_scaled(self):
        """
        Zwraca zdjęcie zeskalowane do rozmiaru zapisanego w
        self.scale.
        """
        scale = self.scale.round()
        img = self.Scale(scale.x, scale.y)
        return img

    def get_bitmap(self, dc):
        """
        Zwraca bitmapę kompatybilną z obecnym Device Context.
        """
        if self.bitmap_cache and self.bitmap_cache[0] == self.scale:
            return self.bitmap_cache[1]
        bmp = wx.Bitmap(self.get_scaled(), dc)
        self.bitmap_cache = [self.scale, bmp]
        return bmp

    def copy(self, copy_area):
        """
        Tworzy kopię wybranego fragmentu tego zdjęcia.
        """
        try:
            copy = self.GetSubImage(copy_area)
        except wx.wxAssertionError:
            return None
        return Image(copy)

    def paste(self, *args, **kwargs):
        """
        Przeciążenie metody wx.Image.Paste() usuwające
        wartość self.bitmap_cache, aby można było zobaczyć
        efekt wklejenia.
        """
        self.bitmap_cache = None
        return self.Paste(*args, **kwargs)

    def get_scale_factor(self):
        """
        Zwraca stosunek oryginalnej wielkości zdjęcia, do zeskalowanej.
        """
        return Point(
                self.scale.x / self.GetWidth(),
                self.scale.y / self.GetHeight()
        )


class ImageView(wx.Panel):
    """
    Widok edycyjny zdjęcia z możliwością zaznaczenia fragmentu zdjęcia
    i wklejenia zaznaczonego fragmentu w wybrane miejsce.
    """

    def __init__(self, image, colours, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.img = Image(image)
        self.img_cp = None
        self.colours = colours
        self.selected_area = SelectedArea()
        self.rescale_lock = True
        self.mouse_pos_lock = False
        self.mouse_pos = None
        self.window_dc = None
        self.Bind(wx.EVT_PAINT, self.__paint__)
        self.Bind(wx.EVT_LEFT_DOWN, self.__on_mouse_down__)
        self.Bind(wx.EVT_LEFT_UP, self.__on_mouse_up__)
        self.Bind(wx.EVT_MOTION, self.__on_mousemove__)
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
        zaznaczonego na zdjęciu, jeżeli takowy istnieje
        oraz rozmiaru kopii zdjęcia jeżeli fragment
        zdjęcia został skopiowany.
        """
        parent = self.GetParent()
        if parent.IsShownOnScreen():
            container_size = Point(self.GetSize())
            scaling = self.__scale_to_fit__(container_size, self.img.scale)
            self.img.update_scale(scaling.scale)
            if not self.rescale_lock:
                if self.selected_area.is_selected():
                    self.selected_area *= scaling.factor()
                if self.img_cp:
                    new_scale = self.img_cp.scale * scaling.factor()
                    self.img_cp.update_scale(new_scale)

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
        pen = wx.Pen(self.colours.get("border"), width=2, style=wx.PENSTYLE_LONG_DASH)
        brush = wx.Brush(wx.Colour(0, 0, 0, wx.ALPHA_TRANSPARENT))
        dc.SetPen(pen)
        dc.SetBrush(brush)
        offset = self.__get_top_left__()
        top_left = self.selected_area.get_top_left_translated(offset)
        top_left = top_left.round()
        width_height = self.selected_area.get_width_height()
        width_height = width_height.round()
        dc.DrawRectangle(top_left.x, top_left.y, width_height.x, width_height.y)

    def __calc_img_cp_pos__(self):
        pos = (self.mouse_pos - self.img_cp.scale / 2).round()
        return Point(pos.x, pos.y)

    def __draw_copy_prev__(self, dc):
        if self.img_cp:
            bmp = self.img_cp.get_bitmap(dc)
            pos = self.__calc_img_cp_pos__()
            dc.DrawBitmap(bmp, pos.x, pos.y)

    def __paint__(self, _):
        dc = wx.GCDC(wx.PaintDC(self))
        self.__draw_image__(dc)
        self.__draw_selection__(dc)
        self.__draw_copy_prev__(dc)

    def __get_window_dc__(self):
        if self.window_dc is None:
            self.window_dc = wx.WindowDC(self)
        return self.window_dc

    def __scale_to_full_size__(self, coord):
        """
        Przeskaluj koordynaty z wielkości okna do
        pełnej wielkości zdjęcia.
        """
        ratio = coord.x / coord.y
        scale_factor_x = self.img.scale.x / self.img.GetWidth()
        scale_x = coord.x / scale_factor_x
        scale_y = scale_x / ratio
        return Point(scale_x, scale_y)

    def save_file(self, filename):
        """
        Funkcja używana przez obiekty klasy MainFrame
        do zapisu zdjęcia.
        """
        self.img.SaveFile(filename)

    def __on_mouse_down__(self, _):
        if self.img_cp:
            # Wklej zdjęcie.
            img_cp_center = self.img_cp.scale / 2
            converted = self.mouse_pos - self.__get_top_left__() - img_cp_center
            converted = self.__scale_to_full_size__(converted).round()
            self.img.paste(self.img_cp, converted.x, converted.y)
        self.img_cp = None
        self.selected_area = SelectedArea(self.mouse_pos - self.__get_top_left__())
        self.Refresh()

    def __on_mouse_up__(self, _):
        if self.selected_area.is_selected():
            factor = self.img.get_scale_factor()
            full_select = self.selected_area / factor
            self.img_cp = self.img.copy(full_select.to_wx_rect())
            if not self.img_cp:
                self.selected_area = SelectedArea()
            else:
                new_scale = self.img_cp.scale * factor
                self.img_cp.update_scale(new_scale)
            self.Refresh()

    def __on_mousemove__(self, event):
        if event.Leaving():
            # Zatrzymaj aktualizowanie pozycji kursora
            # jeżeli nie jest on w środku okna.
            self.mouse_pos_lock = True
        elif event.Entering():
            self.mouse_pos_lock = False
        if not self.mouse_pos_lock:
            self.mouse_pos = Point(event.GetLogicalPosition(self.__get_window_dc__()).Get())
            if event.Dragging():
                self.rescale_lock = True
                self.selected_area.close(self.mouse_pos - self.__get_top_left__())
            if self.selected_area.is_selected():
                self.Refresh()

    def __on_resize__(self, _):
        self.rescale_lock = False


class MainFrame(wx.Frame):
    """
    Główne okno interfejsu graficznego.
    """

    def __init__(self, colours, filename):
        super().__init__(None, title="korektor", size=(924, 512))
        self.SetBackgroundColour(colours.get("background"))
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.image_view = ImageView(filename, colours, self)
        self.sizer.Add(self.image_view, proportion=1, flag=wx.EXPAND)
        self.SetSizer(self.sizer)
        self.__make_menu_bar__()
        self.Show()

    def __make_menu_bar__(self):
        """
        Wstążka z menu plików, które zawiera opcje wyjścia, pokazania
        informacji na temat tej aplikacji oraz opcją zapisania pliku.
        Na MacOS opcje Quit i About są wrzucane automatycznie do osobnego menu
        o nazwie takiej samej jak nazwa aplikacji.
        """
        file_menu = wx.Menu()
        ex = file_menu.Append(wx.ID_EXIT, "Quit", "Quit application.")
        about = file_menu.Append(wx.ID_ABOUT, "About korektor", "Show about info.")
        save = file_menu.Append(wx.ID_SAVE, "Save", "Save the file.")
        menu_bar = wx.MenuBar()
        menu_bar.Append(file_menu, "&File")
        self.SetMenuBar(menu_bar)

        # Dodawanie akcji do przycisków.
        self.Bind(wx.EVT_MENU, self.__on_exit__, ex)
        self.Bind(wx.EVT_MENU, self.__on_about__, about)
        self.Bind(wx.EVT_MENU, self.__on_save__, save)

    def __on_exit__(self, _):
        self.Close(True)

    def __on_about__(self, _):
        wx.MessageBox("korektor\n Copyright (C) Jakub Piśkiewicz 2022", "About korektor")

    def __on_save__(self, _):
        filename = FileDialog(self, "save").get_filename()
        self.image_view.save_file(filename)


class Korektor(wx.App):
    """
    Obiekt tej klasy uruchamia interfejs graficzny gdy powstaje.
    """

    NAME = "korektor"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.SetAppName(self.NAME)
        self.SetAppDisplayName(self.NAME)
        filename = FileDialog(None, "open").get_filename()
        if not filename:
            self.Destroy()
            return
        mf = MainFrame(Colours(), filename)
        self.SetTopWindow(mf)
        self.MainLoop()


if __name__ == '__main__':
    Korektor()
