import React, { useRef, useState, useEffect } from "react";
import "./App.css";

function App() {
  const [tab, setTab] = useState("predict");
  const videoRef = useRef(null);
  const [prediction, setPrediction] = useState("");
  const [sentence, setSentence] = useState("");

  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoRef.current.srcObject = stream;
  };

  const predictFrame = async () => {
    const canvas = document.createElement("canvas");
    canvas.width = 300;
    canvas.height = 300;

    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, 300, 300);

    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("file", blob);

      const res = await fetch("http://127.0.0.1:8000/predict", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      setPrediction(data.label);
    }, "image/jpeg");
  };

  // Real-time prediction
  useEffect(() => {
    if (tab === "predict") {
      const interval = setInterval(() => {
        if (videoRef.current) predictFrame();
      }, 800);
      return () => clearInterval(interval);
    }
  }, [tab]);

  const addLetter = () => {
    if (prediction) setSentence((prev) => prev + prediction);
  };

  return (
    <div>
      <div className="header">🤟 AI Sign Language Tutor</div>

      {/* Tabs */}
      <div className="tabs">
        {["guide", "predict", "quiz", "sentence"].map((t) => (
          <button
            key={t}
            className={`tab-btn ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {/* GUIDE */}
      {tab === "guide" && (
        <div className="grid">
          {"ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("").map((l) => (
            <div key={l} className="card">
              <img
                src={`/data/guide_images/Sign_language_${l}.svg.png`}
                alt={l}
              />
              <div>{l}</div>
            </div>
          ))}
        </div>
      )}

      {/* PREDICT */}
      {tab === "predict" && (
        <div style={{ textAlign: "center" }}>
          <div className="camera-card">
            <video ref={videoRef} autoPlay width="300" />
          </div>

          <button className="btn" onClick={startCamera}>
            Start Camera
          </button>

          <h2>Prediction: {prediction}</h2>
        </div>
      )}

      {/* QUIZ */}
      {tab === "quiz" && (
        <div style={{ textAlign: "center" }}>
          <h2>Quiz Mode Coming Next 🚀</h2>
        </div>
      )}

      {/* SENTENCE */}
      {tab === "sentence" && (
        <div style={{ textAlign: "center" }}>
          <video ref={videoRef} autoPlay width="300" />

          <br />

          <button className="btn" onClick={startCamera}>
            Start Camera
          </button>

          <button className="btn" onClick={addLetter}>
            Add Letter
          </button>

          <h2>Sentence: {sentence}</h2>
        </div>
      )}
    </div>
  );
}

export default App;