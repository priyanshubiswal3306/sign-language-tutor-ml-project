import React, { useRef, useState, useEffect } from "react";
import "./App.css";

function App() {
  const videoRef = useRef(null);

  const [tab, setTab] = useState("predict");
  const [prediction, setPrediction] = useState("");

  // ================= SENTENCE =================
  const [sentence, setSentence] = useState("");
  const lastAddedRef = useRef("");
  const lastTimeRef = useRef(0);
  const stableRef = useRef("");
  const stableCountRef = useRef(0);

  // ================= QUIZ =================
  const letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
  const [target, setTarget] = useState("");
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [timer, setTimer] = useState(5);
  const timerRef = useRef(null);
  const MAX_Q = 30;

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
      setPrediction(data.label);
    }, "image/jpeg");
  };

  // ================= REAL-TIME LOOP =================
  useEffect(() => {
    const interval = setInterval(() => {
      predictFrame();
    }, 800);

    return () => clearInterval(interval);
  }, []);

  // ================= SENTENCE STABILITY =================
  useEffect(() => {
    const now = Date.now();

    if (tab !== "sentence" || !prediction) return;

    if (prediction === stableRef.current) {
      stableCountRef.current += 1;
    } else {
      stableRef.current = prediction;
      stableCountRef.current = 1;
    }

    if (
      stableCountRef.current > 3 &&
      prediction !== lastAddedRef.current &&
      now - lastTimeRef.current > 1500
    ) {
      setSentence((prev) => prev + prediction);

      lastAddedRef.current = prediction;
      lastTimeRef.current = now;
      stableCountRef.current = 0;
    }
  }, [prediction, tab]);

  // ================= QUIZ =================
  const startQuiz = () => {
    setScore(0);
    setTotal(0);
    nextQuestion();
  };

  const nextQuestion = () => {
    setTarget(letters[Math.floor(Math.random() * letters.length)]);
    setTimer(5);

    clearInterval(timerRef.current);

    timerRef.current = setInterval(() => {
      setTimer((t) => {
        if (t <= 1) {
          clearInterval(timerRef.current);
          setTotal((prev) => prev + 1); // wrong
          nextQuestion();
          return 5;
        }
        return t - 1;
      });
    }, 1000);
  };

  // Check correct answer
  useEffect(() => {
    if (tab === "quiz" && prediction && target && total < MAX_Q) {
      if (prediction === target) {
        clearInterval(timerRef.current);

        setScore((s) => s + 1);
        setTotal((t) => t + 1);

        nextQuestion();
      }
    }
  }, [prediction, tab]);

  // ================= UI =================
  return (
    <div className="app">

      <h1 className="title">🤟 AI Sign Language Tutor</h1>

      {/* TABS */}
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

      {/* GUIDE */}
      {tab === "guide" && (
        <div className="grid">
          {letters.map((l) => (
            <div key={l} className="card">
              <img src={`/data/guide_images/Sign_language_${l}.png`} alt={l} />
              <p>{l}</p>
            </div>
          ))}
        </div>
      )}

      {/* PREDICT */}
      {tab === "predict" && (
        <div className="center">
          <div className="camera">
            <video ref={videoRef} autoPlay />
          </div>

          <button className="btn" onClick={startCamera}>
            Start Camera
          </button>

          <h2 className="output">Prediction: {prediction}</h2>
        </div>
      )}

      {/* QUIZ */}
      {tab === "quiz" && (
        <div className="center">
          <div className="camera">
            <video ref={videoRef} autoPlay />
          </div>

          <button className="btn" onClick={startCamera}>
            Start Camera
          </button>

          <button className="btn blue" onClick={startQuiz}>
            Start Quiz
          </button>

          <h2>Target: {target}</h2>
          <h2>⏱ Time Left: {timer}s</h2>
          <h2>Score: {score}/{total}</h2>

          {total >= MAX_Q && (
            <h2 className="result">
              Final Score: {score}/{MAX_Q}
            </h2>
          )}
        </div>
      )}

      {/* SENTENCE */}
      {tab === "sentence" && (
        <div className="center">
          <div className="camera">
            <video ref={videoRef} autoPlay />
          </div>

          <button className="btn" onClick={startCamera}>
            Start Camera
          </button>

          <h2 className="sentence">{sentence}</h2>
        </div>
      )}
    </div>
  );
}

export default App;