from fileinput import filename
from typing import Union

from fastapi import FastAPI, File, UploadFile, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from PIL import Image, ExifTags
from uuid import uuid4
import sqlite3
from datetime import datetime
import os, sys
import hashlib
from fastapi.middleware.cors import CORSMiddleware

os.chdir("./data")

origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://localhost:3000",
]

app = FastAPI(
    docs_url=None,
    redoc_url=None
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
db = sqlite3.connect("images.db")
cursor = db.cursor()
cursor.execute(
    "CREATE TABLE IF NOT EXISTS images (uuid TEXT PRIMARY KEY, filename TEXT, Make TEXT, Model TEXT, DateTimeOriginal INT, ExposureTime FLOAT, FNumber FLOAT, ISOSpeedRatings INT, FocalLengthIn35mmFilm INT, LensModel TEXT, ExposureBiasValue FLOAT, Software TEXT, exif_all TEXT)"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS info (uuid TEXT PRIMARY KEY, title TEXT, description TEXT)"
)
cursor.execute(
    "CREATE TABLE IF NOT EXISTS hashtable (hash TEXT PRIMARY KEY, uuid TEXT)"
)
db.commit()

os.path.exists("images") or os.makedirs("images")
os.path.exists("thumbnails") or os.makedirs("thumbnails")

SUPPORTED_IMAGE_FORMATS = ["jpg", "jpeg", "png", "gif"]
DB_IMAGE_COLUMNS = [
    "uuid",
    "filename",
    "Make",
    "Model",
    "DateTimeOriginal",
    "ExposureTime",
    "FNumber",
    "ISOSpeedRatings",
    "FocalLengthIn35mmFilm",
    "LensModel",
    "ExposureBiasValue",
    "Software",
    "exif_all",
]
DB_INFO_COLUMNS = ["uuid", "title", "description"]
DB_HASHTABLE_COLUMNS = ["hash", "uuid"]


@app.get("/", response_class=HTMLResponse)
def test():
    return "Hello"


@app.post("/api/image")
@app.put("/api/image")
async def image_upload(file: UploadFile = File(...), sha1: str = None):
    if "." not in file.filename:
        raise HTTPException(415, {"error": "File has no extension"})

    file_extension = file.filename.split(".")[-1]
    if file_extension.lower() not in SUPPORTED_IMAGE_FORMATS:
        raise HTTPException(
            415,
            {
                "error": "File is not an image or is not supported. Supported formats: {}".format(
                    SUPPORTED_IMAGE_FORMATS
                )
            },
        )

    # Check if file already exists
    # Pre-check with SHA1 hash provided in the request first
    if sha1:
        uuid = hash_collision_check_with_sha1(sha1)
        if uuid:
            raise HTTPException(409, {"error": "File already exists", "uuid": uuid})
    # Then check with SHA1 hash of the file
    hash, uuid = hash_collision_check(file)
    if uuid:
        raise HTTPException(409, {"error": "File already exists", "uuid": uuid})
    # No collision found, generate new UUID and insert into hashtable
    uuid = str(uuid4())
    cursor.execute(
        "INSERT OR REPLACE INTO hashtable (hash, uuid) VALUES (?, ?)", (hash, uuid)
    )
    db.commit()
    
    # Open the image file with PIL
    with Image.open(file.file) as img:
        # Get the image's EXIF data
        exif_data = img._getexif()
        exif_dict = {}
        # If the image has EXIF data
        if exif_data:
            # Iterate over the EXIF data and print it
            for tag_id, value in exif_data.items():
                tag = ExifTags.TAGS.get(tag_id, tag_id)
                exif_dict[tag] = str(value)
                print(f"{tag:25}: {value}")
        else:
            print("No EXIF data found")

        # Save the image to disk with name in format: <UUID>.<extension>
        file_name = f"{uuid}.{file_extension}"
        img.save(f"images/{file_name}")
        convert_thumbnail(img)
        img.save(f"thumbnails/{file_name}")
        (
            exif_make,
            exif_model,
            exif_datetime_original,
            exif_exposuretime,
            exif_fnumber,
            exif_isospeedratings,
            exif_focallengthin35mmfilm,
            exif_lensmodel,
            exif_exposurebiasvalue,
            exif_software,
        ) = (
            exif_dict.get("Make", None),
            exif_dict.get("Model", None),
            exif_dict.get("DateTimeOriginal", None),
            exif_dict.get("ExposureTime", None),
            exif_dict.get("FNumber", None),
            exif_dict.get("ISOSpeedRatings", None),
            exif_dict.get("FocalLengthIn35mmFilm", None),
            exif_dict.get("LensModel", None),
            exif_dict.get("ExposureBiasValue", None),
            exif_dict.get("Software", None),
        )
        exif_datetime_original = (
            string_to_timestamp(exif_datetime_original)
            if exif_datetime_original
            else None
        )
        exif_exposuretime = float(exif_exposuretime) if exif_exposuretime else None
        exif_fnumber = float(exif_fnumber) if exif_fnumber else None
        exif_isospeedratings = (
            int(exif_isospeedratings) if exif_isospeedratings else None
        )
        exif_focallengthin35mmfilm = (
            int(exif_focallengthin35mmfilm) if exif_focallengthin35mmfilm else None
        )
        exif_exposurebiasvalue = (
            float(exif_exposurebiasvalue) if exif_exposurebiasvalue else None
        )

        cursor.execute(
            "INSERT INTO images (uuid, filename, Make, Model, DateTimeOriginal, ExposureTime, FNumber, ISOSpeedRatings, FocalLengthIn35mmFilm, LensModel, ExposureBiasValue, Software, exif_all) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                str(uuid),
                file_name,
                exif_make,
                exif_model,
                exif_datetime_original,
                exif_exposuretime,
                exif_fnumber,
                exif_isospeedratings,
                exif_focallengthin35mmfilm,
                exif_lensmodel,
                exif_exposurebiasvalue,
                exif_software,
                str(exif_dict),
            ),
        )
        db.commit()
    cursor.execute("SELECT * FROM images WHERE uuid=?", (str(uuid),))

    return fetchone_dict(cursor)


@app.get("/api/image/{uuid}", response_class=FileResponse)
async def get_image(uuid: str, thumbnail: bool = False):
    # Get image filename from database
    cursor.execute("SELECT filename FROM images WHERE uuid=?", (uuid,))
    filename = cursor.fetchone()
    if not filename:
        raise HTTPException(404, {"error": "Image not found"})
    # Get image from images folder
    if thumbnail:
        if not os.path.exists(f"thumbnails/{filename[0]}"):
            generate_thumbnail_from_path_and_save(f"images/{filename[0]}")
        return f"thumbnails/{filename[0]}"
    return f"images/{filename[0]}"


@app.get("/api/image")
async def get_image(column: list[str] = Query(None), sort: str = "DateTimeOriginal"):
    sort = sort if sort in DB_IMAGE_COLUMNS else "DateTimeOriginal"
    if column:
        column = [col for col in column if col in DB_IMAGE_COLUMNS]
    if column:
        column = ", ".join(column)
        cursor.execute(f"SELECT {column} FROM images ORDER BY {sort}")
    else:
        cursor.execute(f"SELECT * FROM images ORDER BY {sort}")

    return fetchall_dict(cursor)


@app.get("/api/image/{uuid}/exif")
async def get_image_exif(uuid: str, column: list[str] = Query(None)):
    if column:
        column = [col for col in column if col in DB_IMAGE_COLUMNS]
    if column:
        column = ", ".join(column)
        cursor.execute(f"SELECT {column} FROM images WHERE uuid=?", (uuid,))
    else:
        cursor.execute("SELECT * FROM images WHERE uuid=?", (uuid,))

    result = fetchone_dict(cursor)
    if not result:
        raise HTTPException(404, {"error": "Record not found"})
    return result


@app.delete("/api/image/{uuid}")
async def delete_image(uuid: str):
    cursor.execute("SELECT filename FROM images WHERE uuid=?", (uuid,))
    filename = cursor.fetchone()
    if not filename:
        raise HTTPException(404, {"error": "Image not found"})
    cursor.execute("DELETE FROM images WHERE uuid=?", (uuid,))
    cursor.execute("DELETE FROM info WHERE uuid=?", (uuid,))
    cursor.execute("DELETE FROM hashtable WHERE uuid=?", (uuid,))
    db.commit()
    os.remove(f"images/{filename[0]}")
    try:
        os.remove(f"thumbnails/{filename[0]}")
    except FileNotFoundError:
        pass
    return


### Descriptions about images


@app.get("/api/image/{uuid}/info")
async def get_image_description(uuid: str):
    cursor.execute("SELECT * FROM info WHERE uuid=?", (uuid,))

    result = fetchone_dict(cursor)
    if not result:
        raise HTTPException(404, {"error": "Record not found"})
    return result


@app.put("/api/image/{uuid}/info")
async def set_image_description(uuid: str, title: str, description: str):
    cursor.execute(
        "INSERT OR REPLACE INTO info (uuid, title, description) VALUES (?, ?, ?)",
        (uuid, title, description),
    )
    db.commit()
    cursor.execute("SELECT * FROM info WHERE uuid=?", (uuid,))

    result = fetchone_dict(cursor)
    return result


@app.post("/api/image/{uuid}/info")
async def set_image_description(uuid: str, title: str = None, description: str = None):
    record = []
    sql_query = f"UPDATE info SET "
    if title:
        sql_query += f"title=?,"
        record.append(title)
    if description:
        sql_query += f"description=?,"
        record.append(description)
    sql_query = sql_query[:-1] + " WHERE uuid=?"
    record.append(uuid)
    print(sql_query, record)
    db.execute(sql_query, record)
    db.commit()
    cursor.execute("SELECT * FROM info WHERE uuid=?", (uuid,))

    result = fetchone_dict(cursor)
    if not result:
        raise HTTPException(404, {"error": "Record not found"})
    return result


### Helper functions


def string_to_timestamp(datetime_original_string: str) -> int:
    return int(
        datetime.strptime(datetime_original_string, "%Y:%m:%d %H:%M:%S").timestamp()
    )


def fetchone_dict(cursor: sqlite3.Cursor) -> dict:
    record = cursor.fetchone()
    if not record:
        return {}
    else:
        return {k[0]: v for k, v in zip(cursor.description, record)}


def fetchall_dict(cursor: sqlite3.Cursor) -> list[dict]:
    return [
        {k[0]: v for k, v in zip(cursor.description, row)} for row in cursor.fetchall()
    ]


def hash_collision_check_with_sha1(sha1: str) -> bool:
    cursor.execute("SELECT uuid FROM hashtable WHERE hash=?", (sha1,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


def hash_collision_check(file: UploadFile) -> bool:
    hash = hashlib.sha1(file.file.read()).hexdigest()
    uuid = hash_collision_check_with_sha1(hash)
    file.file.seek(0)
    return hash, uuid


def generate_thumbnail_from_path_and_save(
    image_path: str, size: tuple[int, int] = (3000, 300)
):
    with Image.open(image_path) as img:
        thumbnail = convert_thumbnail(img, size)
        thumbnail.save(image_path.replace("images/", "thumbnails/"))


def convert_thumbnail(image: Image, size: tuple[int, int] = (3000, 300)):
    image.thumbnail(size)
