// App.js File
import React, { Component, useState, useEffect, useRef } from "react";
import Container from "react-bootstrap/Container";
import Row from "react-bootstrap/Row";
import Col from "react-bootstrap/Col";
import Button from "react-bootstrap/Button";
import InputGroup from "react-bootstrap/InputGroup";
import FormControl from "react-bootstrap/FormControl";
import ListGroup from "react-bootstrap/ListGroup";
import Image from "react-bootstrap/Image";
import Card from "react-bootstrap/Card";
import Spinner from 'react-bootstrap/Spinner';

export default function App() {
    const [images, setImages] = useState([]);
    useEffect(() => {
        fetch("/api/image")
            .then((response) => response.json())
            .then((data) => {
                setImages(data);
            });
    }, []);
    const inputFile = useRef(null);
    const [isShowingDetails, setIsShowingDetails] = useState(false);
    const [showingImageUuid, setShowingImageUuid] = useState("");
    const [isShowingInfo, setIsShowingInfo] = useState(false);
    const [showingImageInfo, setShowingImageInfo] = useState({});
    const [showingImageExif, setShowingImageExif] = useState({});

    function uploadImage() {
        inputFile.current.click();
        inputFile.current.onchange = () => {
            const file = inputFile.current.files[0];
            const formData = new FormData();
            formData.append("file", file);
            fetch("/api/image", {
                method: "POST",
                body: formData,
            })
                .then((response) => {
                    if (response.status === 409) {
                        throw alert("Image already exists");
                    }
                    if (!response.ok) {
                        throw alert(`Upload failed with status ${response.status}`);
                    }
                    return response.json();
                })
                .then((data) => {
                    setImages([...images, data]);
                })
        };
    }


    const resetViewer = () => {
        setIsShowingDetails(false);
        setShowingImageUuid("");
        // setShowingImageInfo({});
        // setShowingImageExif({});
        setIsShowingInfo(false);
    }

    const toggleShowInfo = () => {
        setIsShowingInfo(!isShowingInfo);
    }


    return (
        <>

            <Container fluid className={isShowingDetails ? "viewer" : "viewer hidden"} style={{ top: 0, left: 0, width: "100vw", height: "100vh" }} >
                <Row style={{ width: "100%", height: "100%" }} className="viewer-card" onClick={resetViewer}>
                    <Col className="viewer-card" style={{ width: "100%", height: "100%" }} >
                        <Card className="viewer-card align-items-center" style={{
                            width: "100%", height: "100%"
                        }}>
                            <Card.Img className="viewer-card mx-auto d-block" src={isShowingDetails ? "/api/image/" + showingImageUuid : ""} style={{ maxWidth: "100%", maxHeight: "100%" }} />
                            <Card.ImgOverlay className={isShowingInfo ? "viewer-card position-absolute bottom-0" : "viewer-card position-absolute bottom-0 hidden"} style={{ left: 0, width: "100%", height: "auto" }} onClick={toggleShowInfo}>
                                <Card.Title className="viewer-card">{showingImageInfo.title}</Card.Title>
                                <Card.Text className="viewer-card">
                                    {showingImageInfo.description}
                                    <div>
                                        <div><b>{showingImageExif.Make ?? "??"} {showingImageExif.Model ?? "??"} + {showingImageExif.LensModel ?? "??"}</b> | {showingImageExif.ExposureTime ? (showingImageExif.ExposureTime > 1 ? showingImageExif.ExposureTime : "1/" + 1 / showingImageExif.ExposureTime) : "??"}s f/{showingImageExif.FNumber ?? "??"} ISO{showingImageExif.ISOSpeedRatings ?? "??"} { showingImageExif.FocalLengthIn35mmFilm ?? "??" }mm</div>
                                        <div>{new Date(showingImageExif.DateTimeOriginal * 1000).toLocaleString()}</div>
                                    </div>
                                </Card.Text>
                            </Card.ImgOverlay>
                        </Card>
                    </Col>
                </Row>
                <Button className="position-absolute top-0 end-0 info" style={{ zIndex: 1000 }} onClick={toggleShowInfo}><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-info-circle-fill" viewBox="0 0 16 16">
                    <path d="M8 16A8 8 0 1 0 8 0a8 8 0 0 0 0 16m.93-9.412-1 4.705c-.07.34.029.533.304.533.194 0 .487-.07.686-.246l-.088.416c-.287.346-.92.598-1.465.598-.703 0-1.002-.422-.808-1.319l.738-3.468c.064-.293.006-.399-.287-.47l-.451-.081.082-.381 2.29-.287zM8 5.5a1 1 0 1 1 0-2 1 1 0 0 1 0 2" />
                </svg></Button>
            </Container>
            <Container fluid className="main">
                <Row>
                    <Col className="header">
                        photographed by <b>Merlyn</b>
                    </Col>
                    <Col xs="auto">
                        <input type='file' id='imageUploadInput' ref={inputFile} style={{ display: 'none' }} />
                        <Button onClick={uploadImage} style={{ display: "none" }}><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-cloud-upload-fill" viewBox="0 0 16 16">
                            <path fill-rule="evenodd" d="M8 0a5.53 5.53 0 0 0-3.594 1.342c-.766.66-1.321 1.52-1.464 2.383C1.266 4.095 0 5.555 0 7.318 0 9.366 1.708 11 3.781 11H7.5V5.707L5.354 7.854a.5.5 0 1 1-.708-.708l3-3a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 5.707V11h4.188C14.502 11 16 9.57 16 7.773c0-1.636-1.242-2.969-2.834-3.194C12.923 1.999 10.69 0 8 0m-.5 14.5V11h1v3.5a.5.5 0 0 1-1 0" />
                        </svg></Button>
                    </Col>

                </Row>

                <Row className="gallery d-flex align-items-center justify-content-center" >
                    {images.map((image, index) => {
                        return (
                            <ImageCard uuid={image.uuid} onclick={() => {
                                setShowingImageUuid(image.uuid);
                                setIsShowingDetails(true);
                                fetch("/api/image/" + image.uuid + "/info")
                                    .then((response) => response.json())
                                    .then((data) => {
                                        setShowingImageInfo(data);
                                    });
                                fetch("/api/image/" + image.uuid + "/exif")
                                    .then((response) => response.json())
                                    .then((data) => {
                                        setShowingImageExif(data);
                                    });

                            }}
                            ></ImageCard>
                        );
                    })}
                </Row>
            </Container>
        </>
    );
}

function ImageCard({ uuid, onclick }) {
    const [info, setInfo] = useState({});
    const [showingDetails, setShowingDetails] = useState(false);

    useEffect(() => {
        fetch("/api/image/" + uuid + "/info")
            .then((response) => response.json())
            .then((data) => {
                if (!data.title) {
                    data.title = "-";
                }
                if (!data.description) {
                    data.description = "";
                }
                setInfo(data);
            });
    }, []);



    return (

        <Col xs="auto" className="d-inline-block" style={{ height: "10vw", minHeight: "100px", padding: "0.5vw 0.5vw" }}>
            <Card className="d-inline-block thumb h-100" style={{}} onClick={onclick}>
                <Card.Img className="h-100 d-inline-block thumb" src={"/api/image/" + uuid + "?thumbnail=true"}></Card.Img>
                <Card.ImgOverlay className="thumb">
                    <Card.Text className="thumb"><b>{info.title}</b></Card.Text>
                    {/* <Card.Text className="thumb">{info.description}</Card.Text> */}
                </Card.ImgOverlay>

            </Card >
        </Col>
    );
}
