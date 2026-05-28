import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Tuple, Dict, Any, List, Optional
import numpy as np

class ChartRecommender:
    """Analyzes query result dataframes to recommend and automatically build ideal interactive Plotly charts."""

    @staticmethod
    def identify_column_types(df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
        """Classifies DataFrame columns into Numeric, Temporal (Datetime), and Categorical categories."""
        numeric_cols = []
        temporal_cols = []
        categorical_cols = []

        for col in df.columns:
            # Check for datetime type
            if pd.api.types.is_datetime64_any_dtype(df[col]):
                temporal_cols.append(col)
                continue
                
            # Attempt to check if column contains date strings
            if df[col].dtype == 'object':
                # Quick sample checks to see if it parses to date
                sample = df[col].dropna().head(5)
                if not sample.empty:
                    try:
                        pd.to_datetime(sample, errors='raise')
                        temporal_cols.append(col)
                        continue
                    except (ValueError, TypeError):
                        pass

            if pd.api.types.is_numeric_dtype(df[col]) and not pd.api.types.is_bool_dtype(df[col]):
                # If numeric but low cardinality integer representing IDs, treat as categorical
                if pd.api.types.is_integer_dtype(df[col]) and df[col].nunique() < 10 and "id" in col.lower():
                    categorical_cols.append(col)
                else:
                    numeric_cols.append(col)
            else:
                categorical_cols.append(col)

        return numeric_cols, temporal_cols, categorical_cols

    def recommend_and_create_chart(self, df: pd.DataFrame) -> Tuple[Optional[str], Optional[go.Figure], List[str]]:
        """
        Analyzes a DataFrame, selects the optimal chart type, builds it,
        and lists alternative visualization formats.
        Returns:
            (recommended_type, plotly_fig_object, list_of_alternatives)
        """
        if df is None or df.empty:
            return None, None, []

        num_cols, temp_cols, cat_cols = self.identify_column_types(df)
        
        # Default empty list of alternatives
        alternatives = []

        # Case 1: Simple 1 Column Data
        if len(df.columns) == 1:
            col = df.columns[0]
            if col in num_cols:
                fig = px.histogram(df, x=col, title=f"Distribution of {col}", template="plotly_white")
                return "histogram", fig, []
            else:
                counts = df[col].value_counts().reset_index()
                counts.columns = [col, "count"]
                fig = px.bar(counts, x=col, y="count", title=f"Frequency Count of {col}", template="plotly_white")
                return "bar", fig, ["pie"] if df[col].nunique() <= 8 else []

        # Case 2: Temporal vs Numeric (Time series)
        if temp_cols and num_cols:
            x_col = temp_cols[0]
            y_col = num_cols[0]
            
            # Sort by date/time to make the lines look correct
            df_sorted = df.copy()
            try:
                df_sorted[x_col] = pd.to_datetime(df_sorted[x_col])
                df_sorted = df_sorted.sort_values(by=x_col)
            except Exception:
                pass
                
            fig = px.line(df_sorted, x=x_col, y=y_col, title=f"{y_col} Over Time ({x_col})", markers=True, template="plotly_white")
            
            alt = ["bar"]
            if len(num_cols) > 1:
                # Add check for secondary line charts if multiple numeric columns exist
                fig = px.line(df_sorted, x=x_col, y=num_cols, title="Comparison Over Time", markers=True, template="plotly_white")
            return "line", fig, alt

        # Case 3: Categorical vs Numeric (Bar charts or Pie charts)
        if cat_cols and num_cols:
            x_col = cat_cols[0]
            y_col = num_cols[0]
            
            # Check cardinality
            cardinality = df[x_col].nunique()
            
            if cardinality <= 6:
                fig = px.pie(df, names=x_col, values=y_col, title=f"Distribution of {y_col} by {x_col}", template="plotly_white")
                return "pie", fig, ["bar"]
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}", template="plotly_white")
                # Rotate axis labels for readability if categories are many
                if cardinality > 8:
                    fig.update_layout(xaxis_tickangle=-45)
                return "bar", fig, ["pie"] if cardinality <= 10 else []

        # Case 4: Numeric vs Numeric (Scatter plots)
        if len(num_cols) >= 2:
            x_col = num_cols[0]
            y_col = num_cols[1]
            color_col = cat_cols[0] if cat_cols else None
            
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=f"{y_col} vs {x_col}", template="plotly_white")
            return "scatter", fig, []

        # Fallback: Just return a generic Bar chart of first columns or a description
        col1 = df.columns[0]
        col2 = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        fig = px.bar(df, x=col1, y=col2, title=f"{col2} by {col1}", template="plotly_white")
        return "bar", fig, []
