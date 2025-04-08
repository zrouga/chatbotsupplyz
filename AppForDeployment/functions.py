import subprocess
import sys
from data_fetching import get_data
import pandas as pd
from pydantic import BaseModel, Field


data = get_data()
invoices, items, purchases, suppliers, clients = (
    data["invoices"][0],
    data["items"][0],
    data["purchases"][0],
    data["suppliers"][0],
    data["clients"][0],
)

DATA = {
    "invoices": invoices,
    "items": items,
    "purchases": purchases,
    "suppliers": suppliers,
    "clients": clients,
}


class QueryAnalysisOutput(BaseModel):
    """
    This function extracts data from a given table based on a filtering condition.
    """

    table_name: str = Field(..., description="Table to extract data from.")
    filtering_condition: str = Field(
        ...,
        description="Filtering condition from the given table str to perform table_name.query('condition') in python. Python-like expressions for filtering",
    )

    def run(self):
        return (
            DATA[self.table_name]
            .query(self.filtering_condition, engine="python")
            .to_json(orient="records")
        )


class InventoryCodeInterpreter(BaseModel):
    """
    This function interprets the inventory code and returns the item name.
     Whenever this tool is called, all imports SHOULD be done again, tool calls are independent.\
    The code should always finish with a print statement as a return.
    """

    python_code: str = Field(
        ...,
        description="Python code (can only use pandas and numpy libraries at most) to execute to respond to the question.The code should always finish with a print statement as a return.",
    )

    def run(self):
        try:
            # execute the python code in a subprocess and enforce error checking
            output = subprocess.run(
                [sys.executable, "-c", self.python_code],
                capture_output=True,
                check=True,  # this causes a CalledProcessError for non-zero exit codes
            )
            return output.stdout.decode()
        except subprocess.CalledProcessError as e:
            # Return the error message instead of raising an exception.
            return f"Error executing the code: {e.stderr.decode()}"
        except Exception as e:
            # Return a generic error message.
            return f"An unexpected error occurred: {str(e)}"
