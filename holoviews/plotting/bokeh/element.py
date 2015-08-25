import param

import bokeh.plotting
from bokeh.models import ColumnDataSource, HoverTool
from bokeh import mpl

from ...core import Store, HoloMap
from ...core.util import match_spec
from ..plot import GenericElementPlot, GenericOverlayPlot

from .plot import BokehPlot


# Define shared style properties for bokeh plots
line_properties = ['line_width', 'line_color', 'line_alpha',
                   'line_join', 'line_cap', 'line_dash']

fill_properties = ['fill_color', 'fill_alpha']

text_properties = ['text_font', 'text_font_size', 'text_font_style', 'text_color',
                   'text_alpha', 'text_align', 'text_baseline']

legend_dimensions = ['label_standoff', 'label_width', 'label_height', 'glyph_width',
                     'glyph_height', 'legend_padding', 'legend_spacing']



class ElementPlot(BokehPlot, GenericElementPlot):

    bgcolor = param.Parameter(default='white', doc="""
        Background color of the plot.""")

    border = param.Number(default=2, doc="""
        Minimum border around plot.""")

    invert_xaxis = param.Boolean(default=False, doc="""
        Whether to invert the plot x-axis.""")

    invert_yaxis = param.Boolean(default=False, doc="""
        Whether to invert the plot y-axis.""")

    show_legend = param.Boolean(default=False, doc="""
        Whether to show legend for the plot.""")

    shared_axes = param.Boolean(default=True, doc="""
        Whether to invert the share axes across plots
        for linked panning and zooming.""")

    title_size = param.String(default='12pt', doc="""
        Title font size to apply to the plot.""")

    xlog = param.Boolean(default=False, doc="""
        Whether the x-axis of the plot will be a log axis.""")

    ylog = param.Boolean(default=False, doc="""
        Whether the x-axis of the plot will be a log axis.""")

    show_legend = param.Boolean(default=False, doc="""
        Whether to show legend for the plot.""")

    tools = param.List(default=['pan', 'wheel_zoom', 'box_zoom',
                                'reset', 'resize'], doc="""
        A list of plugin tools to use on the plot.""")

    xaxis = param.ObjectSelector(default='left',
                                      objects=['left', 'right', 'bare', 'left-bare',
                                               'right-bare', None], doc="""
        Whether and where to display the xaxis, bare options allow suppressing
        all axis labels including ticks and xlabel.""")

    yaxis = param.ObjectSelector(default='bottom',
                                 objects=['top', 'bottom', 'bare', 'top-bare',
                                          'bottom-bare', None], doc="""
        Whether and where to display the yaxis, bare options allow suppressing
        all axis labels including ticks and ylabel.""")

    def __init__(self, element, plot=None, **params):
        super(ElementPlot, self).__init__(element, **params)
        self.style = self.style[self.cyclic_index]
        self.handles = {} if plot is None else self.handles['plot']


    def _init_tools(self, element):
        tools = list(self.tools)
        if 'hover' in tools:
            tooltips = [(d, '@'+d) for d in element.dimensions(label=True)]
            tools[tools.index('hover')] = HoverTool(tooltips=tooltips)
        return tools


    def _init_axes(self, plots, element, ranges):
        xlabel, ylabel, zlabel = self._axis_labels(element, plots)
        plot_ranges = {}
        # Try finding shared ranges in other plots in the same Layout
        if plots and self.shared_axes:
            for plot in plots:
                if plot is None or not hasattr(plot, 'xaxis'): continue
                if plot.xaxis[0].axis_label == xlabel:
                    plot_ranges['x_range'] = plot.x_range
                if plot.xaxis[0].axis_label == ylabel:
                    plot_ranges['y_range'] = plot.x_range
                if plot.yaxis[0].axis_label == ylabel:
                    plot_ranges['y_range'] = plot.y_range
                if plot.yaxis[0].axis_label == xlabel:
                    plot_ranges['x_range'] = plot.y_range

        if not 'x_range' in plot_ranges:
            if 'x_range' in ranges:
                plot_ranges['x_range'] = ranges['x_range']
            else:
                l, _, r, _ = self.get_extents(element, ranges)
                if all(x is not None for x in (l, r)):
                    plot_ranges['x_range'] = [l, r]

        if self.invert_xaxis:
            plot_ranges['x_ranges'] = plot_ranges['x_ranges'][::-1]

        if not 'y_range' in plot_ranges:
            if 'y_range' in ranges:
                plot_ranges['y_range'] = ranges['y_range']
            else:
                _, b, _, t = self.get_extents(element, ranges)
                if all(y is not None for y in (b, t)):
                    plot_ranges['y_range'] = [b, t]
        if self.invert_yaxis:
            plot_ranges['y_range'] = plot_ranges['y_range'][::-1]
        return (xlabel, ylabel, zlabel), plot_ranges


    def _init_plot(self, key, plots, ranges=None):
        """
        Initializes Bokeh figure to draw Element into and sets basic
        figure and axis attributes including axes types, labels,
        titles and plot height and width.
        """

        element = self._get_frame(key)
        subplots = list(self.subplots.values()) if self.subplots else []

        x_axis_type = 'log' if self.xlog else 'linear'
        y_axis_type = 'log' if self.ylog else 'linear'
        labels, plot_ranges = self._init_axes(plots, element, ranges)
        xlabel, ylabel, zlabel = labels
        tools = self._init_tools(element)

        return bokeh.plotting.figure(x_axis_type=x_axis_type,
                                     x_axis_label=xlabel,
                                     y_axis_type=y_axis_type,
                                     y_axis_label=ylabel,
                                     tools=tools, **plot_ranges)


    def _plot_properties(self, key, plot, element):
        title_font = self._fontsize('title', 'title_text_font_size')
        plot_props = dict(plot_height=self.height, plot_width=self.width,
                          title_text_color='black', **title_font)
        if self.show_title:
            plot_props['title'] = self._format_title(key)
        if self.bgcolor:
            plot_props['background_fill'] = self.bgcolor
        if self.border is not None:
            plot_props['min_border'] = self.border
        return plot_props


    def _axis_properties(self, axis, key, plot, element):
        axis_props = {}
        if ((axis == 'x' and self.xaxis in ['left-bare' or None]) or
            (axis == 'y' and self.yaxis in ['bottom-bare' or None])):
            axis_props['axis_label'] = ''
            axis_props['major_label_text_font_size'] = '0pt'
            axis_props['major_tick_line_color'] = None
        return axis_props


    def _update_plot(self, key, plot, element=None):
        """
        Updates plot parameters on every frame
        """
        plot.set(**self._plot_properties(key, plot, element))
        plot.xaxis[0].set(**self._axis_properties('x', key, plot, element))
        plot.yaxis[0].set(**self._axis_properties('y', key, plot, element))


    def _process_legend(self):
        """
        Disables legends if show_legend is disabled.
        """
        if not self.overlaid and not self.show_legend:
            for l in self.handles['plot'].legend:
                l.legends[:] = []
                l.border_line_alpha = 0


    def get_data(self, element, ranges=None):
        """
        Returns the data from an element in the appropriate format for
        initializing or updating a ColumnDataSource.
        """
        raise NotImplementedError


    def _init_datasource(self, element, ranges=None):
        """
        Initializes a data source to be passed into the bokeh glyph.
        """
        return ColumnDataSource(data=self.get_data(element, ranges))


    def _update_datasource(self, source, element, ranges):
        """
        Update datasource with data for a new frame.
        """
        for k, v in self.get_data(element, ranges).items():
            source.data[k] = v


    def _init_glyph(self, element, plot, source, ranges):
        """
        Returns a Bokeh glyph object.
        """
        raise NotImplementedError


    def initialize_plot(self, ranges=None, plot=None, plots=None, source=None):
        """
        Initializes a new plot object with the last available frame.
        """
        element = self.map.last
        key = self.keys[-1]

        ranges = self.compute_ranges(self.map, key, ranges)
        ranges = match_spec(element, ranges)
        if plot is None:
            plot = self._init_plot(key, ranges=ranges, plots=plots)
        if source is None:
            source = self._init_datasource(element, ranges)
        self.handles['plot'] = plot
        self.handles['source'] = source
        self._init_glyph(element, plot, source, ranges)
        if not self.overlaid:
            self._update_plot(key, plot, element)
        self._process_legend()
        self.drawn = True

        return plot


    def update_frame(self, key, ranges=None, plot=None):
        """
        Updates an existing plot with data corresponding
        to the key.
        """

        if plot is None:
            plot = self.handles['plot']
        element = self._get_frame(key)
        if element:
            source = self.handles['source']
            self._update_datasource(source, element, ranges)
            if not self.overlaid:
                self._update_plot(key, plot, element)



class BokehMPLWrapper(ElementPlot):
    """
    Wraps an existing HoloViews matplotlib plot and converts
    it to bokeh.
    """

    def __init__(self, element, plot=None, **params):
        super(ElementPlot, self).__init__(element, **params)
        if isinstance(element, HoloMap):
            etype = element.type
        else:
            etype = type(element)
        plot = Store.registry['matplotlib'][etype]
        self.mplplot = plot(element, **self.lookup_options(element, 'plot').options)


    def initialize_plot(self, ranges=None, plot=None, plots=None):
        element = self.map.last
        key = self.keys[-1]

        self.mplplot.initialize_plot(ranges)
        plot = mpl.to_bokeh(self.mplplot.state)
        self.handles['plot'] = plot
        return plot


    def update_frame(self, key, ranges=None, plot=None):
        if key in self.map:
            self.mplplot.update_frame(key, ranges)
            self.handles['plot'] = mpl.to_bokeh(self.mplplot.state)


class OverlayPlot(GenericOverlayPlot, ElementPlot):

    show_legend = param.Boolean(default=True, doc="""
        Whether to show legend for the plot.""")

    legend_position = param.ObjectSelector(objects=["top_right", "top_left",
                                                    "bottom_left", "bottom_right"],
                                           default="top_right", doc="""
        Allows selecting between a number of predefined legend position
        options. The predefined options may be customized in the
        legend_specs class attribute.""")


    style_opts = legend_dimensions + line_properties + text_properties

    def _process_legend(self):
        plot = self.handles['plot']
        if not self.show_legend or not len(plot.legend):
            super(OverlayPlot, self)._process_legend()
            return

        options = {}
        for k, v in self.style.items():
            if k in line_properties:
                k = 'border_' + k
            elif k in text_properties:
                k = 'label_' + k
            options[k] = v

        legend_labels = []
        plot.legend[0].set(**options)
        plot.legend.orientation = self.legend_position
        legends = plot.legend[0].legends
        new_legends = []
        for label, l in legends:
            if label in legend_labels:
               continue
            legend_labels.append(label)
            new_legends.append((label, l))
        plot.legend[0].legends[:] = new_legends


    def initialize_plot(self, ranges=None, plot=None, plots=None):
        key = self.keys[-1]
        ranges = self.compute_ranges(self.map, key, ranges)
        if plot is None:
            plot = self._init_plot(key, ranges=ranges, plots=plots)
        self.handles['plot'] = plot

        for subplot in self.subplots.values():
            subplot.initialize_plot(ranges, plot, plots)

        self._process_legend()

        return plot


    def update_frame(self, key, ranges=None, plot=None):
        """
        Update the internal state of the Plot to represent the given
        key tuple (where integers represent frames). Returns this
        state.
        """
        for subplot in self.subplots.values():
            subplot.update_frame(key, ranges, plot)
