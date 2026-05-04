import pyqtgraph as pg

class DashboardChart:
    def __init__(self, plot_widget):
        self.plot_widget = plot_widget
        self.plot_widget.setBackground('w')
        self.plot_widget.setYRange(0, 100)
        self.curve = self.plot_widget.plot(pen=pg.mkPen(color='b', width=2))

    def update(self, data):
        self.curve.setData(data)