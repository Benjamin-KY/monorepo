#!/usr/bin/env python
# coding: utf-8

# Copyright (c) Saga Inc.
# Distributed under the terms of the GPL License.

import json
import pandas as pd
from typing import Any, Dict, List
import plotly.express as px
import plotly.graph_objects as go
from mitosheet.step_performers.graph.graph_utils import (
    get_html_and_script_from_figure,
)
from mitosheet.sheet_functions.types.utils import is_number_dtype
from mitosheet.types import ColumnHeader, ColumnID
from mitosheet.mito_analytics import log
from mitosheet.steps_manager import StepsManager

# Max number of unique non-number items to display in a graph.
# NOTE: make sure to change both in unison so they make sense
MAX_UNIQUE_NON_NUMBER_VALUES = 10_000


def get_column_summary_graph(event: Dict[str, Any], steps_manager: StepsManager) -> str:
    """
    Creates a column summary graph and sends it back as a PNG
    string to the frontend for display.
    """
    sheet_index = event['sheet_index']
    column_id = event['column_id']
    height = event['height']
    width = event['width']


    # Create a copy of the dataframe, just for safety.
    df: pd.DataFrame = steps_manager.dfs[sheet_index].copy()

    column_header = steps_manager.curr_step.post_state.column_ids.get_column_header_by_id(sheet_index, column_id)
    fig = _get_column_summary_graph(df, column_header)
        
    # Get rid of some of the default white space
    fig.update_layout(
        margin=dict(
            l=0,
            r=0,
            t=30,
            b=30,
        )
    )

    return_object = get_html_and_script_from_figure(fig, height, width)

    return json.dumps(return_object)

def filter_df_to_top_unique_values_in_series(
    df: pd.DataFrame,
    main_series: pd.Series,
    num_unique_values: int,
) -> pd.Series:
    """
    Helper function for filtering the dataframe down to the top most common
    num_unique_values in the main_series. Will not change the series if there are less
    values than that.

    The function filters the entire dataframe to make sure that the columns stay
    the same length (which is necessary if you want to graph them).

    It returns the filtered dataframe
    """
    if (
        len(main_series) < num_unique_values
        or main_series.nunique() < num_unique_values
    ):
        return df

    value_counts_series = main_series.value_counts()
    most_frequent_values_list = value_counts_series.head(
        n=num_unique_values
    ).index.tolist()

    return df[main_series.isin(most_frequent_values_list)]


def _get_column_summary_graph(df: pd.DataFrame, column_header: ColumnHeader) -> go.Figure:
    """
    One Axis Graphs heuristics:
    1. Number Column - we do no filtering. These graphs are pretty efficient up to 1M rows
    2. Non-number column. We filter to the top 10k values, as the graphs get pretty laggy
       beyond that
    """
    series: pd.Series = df[column_header]
    column_dtype = str(series.dtype)

    graph_title = f"{column_header} Frequencies"

    filtered = False
    if not is_number_dtype(column_dtype):
        if series.nunique() > MAX_UNIQUE_NON_NUMBER_VALUES:
            df = filter_df_to_top_unique_values_in_series(
                df, series, MAX_UNIQUE_NON_NUMBER_VALUES
            )
            # Set series as the newly filtered series
            series = df[column_header]

            filtered = True

        # Fill NaN values with 'NaN' so they are displayed in the graph.
        series = series.fillna("NaN")

    labels = {"x": ""}

    kwargs = {
        "x": series,
        "labels": labels,
        "title": graph_title,
    }

    fig = px.histogram(**kwargs)

    log(f"generate_column_summary_stat_graph", {"param_filtered": filtered})

    return fig
