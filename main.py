from fastapi import FastAPI
from fastapi.responses import JSONResponse
from ingestData.ingestXAPI import ingest_XAPI
from datalake.etl import ETLProcessor as ETL_To_DataLake
from datawarehouse.etl import ETLProcess as ETL_To_DataWarehouse
from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

etl_to_datalake = ETL_To_DataLake()
ingestXAPI = ingest_XAPI()
etl_to_datawarehouse = ETL_To_DataWarehouse()


@app.get("/ingest_data_xapi")
async def IngestData():
    try:
        ingestXAPI.get_statements()
        return JSONResponse(content={"message": "Data Ingested Successfully."}, status_code=200)
    except Exception as e:
        return JSONResponse({"message": f"Data Ingestion Failed: {str(e)}"}, status_code=500)



@app.get("/etl_to_datalake")
async def load_to_datalake():
    try:
        etl_to_datalake.execute()
        message = "ETL to Data Lake completed successfully."
        return JSONResponse(content={"message": message}, status_code=200)

    except Exception as e:
        print(str(e))
        return JSONResponse({"message": f"Load fail: {str(e)}"}, status_code=500)


@app.get("/etl_to_datawarehouse")
async def load_to_datawarehouse():

    try:
        etl_to_datawarehouse.execute()
        message = "ETL to Data Warehouse completed successfully."
        return JSONResponse(content={"message": message}, status_code=200)

    except Exception as e:
        print(str(e))

        return JSONResponse({"message": f"Load fail: {str(e)}"}, status_code=500)

