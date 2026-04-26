import React, { useRef, useState, useEffect } from "react";
import "./App.css";

function App() {
  const videoRef = useRef(null);

  const [tab, setTab] = useState("sentence");
  const [prediction, setPrediction] = useState("");
  const [sentence, setSentence] = useState("");

  // ================= BUFFER (KEY FIX) =================
  const bufferRef = useRef([]);
  const BUFFER_SIZE = 5;

  const lastAddedRef = useRef("");
  const cooldownRef = useRef(false);

  // ================= CAMERA =================
  const startCamera = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    videoRef.current.srcObject = stream;
  };

  // ================= PREDICT =================
  const predictFrame = async () => {
    if (!videoRef.current) return;

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
      setPrediction(data.label ? data.label.trim() : "");
    }, "image/jpeg");
  };

  // ================= REAL-TIME LOOP =================
  useEffect(() => {
    const interval = setInterval(() => {
      predictFrame();
    }, 500);

    return () => clearInterval(interval);
  }, []);

  // ================= STABLE PREDICTION =================
  const getStablePrediction = () => {
    const counts = {};
    bufferRef.current.forEach((p) => {
      if (!p) return;
      counts[p] = (counts[p] || 0) + 1;
    });

    let max = 0;
    let best = "";

    for (let key in counts) {
      if (counts[key] > max) {
        max = counts[key];
        best = key;
      }
    }

    // require majority
    if (max >= 3) return best;

    return "";
  };

  // ================= SENTENCE LOGIC (FINAL FIX) =================
  useEffect(() => {
    if (tab !== "sentence") return;

    // update buffer
    bufferRef.current.push(prediction);
    if (bufferRef.current.length > BUFFER_SIZE) {
      bufferRef.current.shift();
    }

    const stable = getStablePrediction();

    if (!stable) return;

    // prevent duplicate spam
    if (stable === lastAddedRef.current) return;

    if (cooldownRef.current) return;

    // ADD LETTER
    setSentence((prev) => prev + stable);

    lastAddedRef.current = stable;

    // cooldown (prevents fast repeats)
    cooldownRef.current = true;
    setTimeout(() => {
      cooldownRef.current = false;
    }, 800);
  }, [prediction, tab]);

  // ================= KEYBOARD SUPPORT =================
  useEffect(() => {
    const handleKey = (e) => {
      if (tab !== "sentence") return;

      if (e.key === " ") {
        setSentence((prev) => prev + " ");
      }

      if (e.key === "Backspace") {
        setSentence((prev) => prev.slice(0, -1));
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [tab]);

  // ================= UI =================
  return (
    <div className="app">

      <h1 className="title">🤟 AI Sign Language Tutor</h1>

      <div className="tabs">
        {["guide", "predict", "quiz", "sentence"].map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? "active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      {/* CAMERA */}
      <div className="center">
        <div className="camera">
          <video ref={videoRef} autoPlay />
        </div>

        <button className="btn" onClick={startCamera}>
          Start Camera
        </button>

        <h3>Live Prediction: {prediction || "None"}</h3>
      </div>

      {/* SENTENCE */}
      {tab === "sentence" && (
        <div className="center">
          <h2 className="sentence">{sentence}</h2>

          <p className="hint">
            Space = SPACE key | Delete = BACKSPACE
          </p>

          <button className="btn red" onClick={() => setSentence("")}>
            Clear
          </button>
        </div>
      )}
    </div>
  );
}

export default App;