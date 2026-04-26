import React, { useRef, useState, useEffect, useCallback } from "react";
import "./App.css";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const MAX_Q = 30;

function App() {
  // ================= REFS =================
  const videoRef = useRef(null);
  const tabRef = useRef("predict");

  // Sentence Refs
  const stableCharRef = useRef("");
  const stableCountRef = useRef(0);
  const lastAddedRef = useRef("");

  // Quiz Refs
  const quizActiveRef = useRef(false);
  const quizTargetRef = useRef("");
  const quizStartTimeRef = useRef(0); 
  const handDetectedRef = useRef(false); // Tracks if the hand has entered the frame yet

  // ================= STATES =================
  const [tab, setTabState] = useState("predict");
  const [prediction, setPrediction] = useState("");
  const [isCameraRunning, setIsCameraRunning] = useState(false);

  // Sentence State
  const [sentence, setSentence] = useState("");

  // Quiz State
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [target, setTarget] = useState("");

  // ================= HELPERS =================
  const setTab = (newTab) => {
    setTabState(newTab);
    tabRef.current = newTab;
  };

  // ================= CAMERA =================
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setIsCameraRunning(true);
      }
    } catch (err) {
      console.error("Failed to start camera:", err);
      alert("Please allow camera access.");
    }
  };

  // ================= PREDICTION & LOGIC LOOP =================
  const processFrame = useCallback(async () => {
    if (!videoRef.current || videoRef.current.readyState < 2) return;

    const canvas = document.createElement("canvas");
    canvas.width = 300;
    canvas.height = 300;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(videoRef.current, 0, 0, 300, 300);

    canvas.toBlob(async (blob) => {
      const formData = new FormData();
      formData.append("file", blob);

      try {
        const res = await fetch("http://127.0.0.1:8000/predict", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        const currentPred = data.label ? data.label.trim() : "";
        
        setPrediction(currentPred);

        // Only run logic if a hand/sign is actually detected
        if (currentPred) {
          handleAppLogic(currentPred);
        }
      } catch (error) {
        console.error("Prediction API Error:", error);
      }
    }, "image/jpeg");
  }, []);

  const handleAppLogic = (currentPred) => {
    const currentTab = tabRef.current;

    // --- SENTENCE LOGIC ---
    if (currentTab === "sentence") {
      if (currentPred === stableCharRef.current) {
        stableCountRef.current += 1;
      } else {
        stableCharRef.current = currentPred;
        stableCountRef.current = 1;
      }

      if (stableCountRef.current >= 3 && currentPred !== lastAddedRef.current) {
        setSentence((prev) => prev + currentPred);
        lastAddedRef.current = currentPred;
        stableCountRef.current = 0;
      }
    }

    // --- QUIZ LOGIC ---
    if (currentTab === "quiz" && quizActiveRef.current) {
      
      // 1. Start the hidden timer the moment the AI detects the hand for the first time
      if (!handDetectedRef.current) {
        handDetectedRef.current = true;
        quizStartTimeRef.current = Date.now();
      }

      // 2. Check for correct answer
      if (currentPred === quizTargetRef.current) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= 2) {
          progressQuiz(true); // Guessed correctly!
        }
      } else {
        stableCountRef.current = 0;
      }
    }
  };

  // ================= QUIZ CONTROLS =================
  const progressQuiz = useCallback((isCorrect) => {
    if (isCorrect) {
      setScore((s) => s + 1);
    }

    setTotal((prevTotal) => {
      const newTotal = prevTotal + 1;
      
      if (newTotal >= MAX_Q) {
        quizActiveRef.current = false;
        return newTotal;
      }

      // Setup next question
      const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
      setTarget(randomLetter);
      quizTargetRef.current = randomLetter;
      stableCountRef.current = 0;
      
      // Pause the timer until the hand is detected again
      handDetectedRef.current = false;
      quizStartTimeRef.current = 0; 
      
      return newTotal;
    });
  }, []);

  const startQuiz = () => {
    setScore(0);
    setTotal(0);
    quizActiveRef.current = true;
    
    // Setup first question
    const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
    setTarget(randomLetter);
    quizTargetRef.current = randomLetter;
    stableCountRef.current = 0;
    
    // Pause the timer until the hand is detected
    handDetectedRef.current = false;
    quizStartTimeRef.current = 0;
  };

  // ================= INTERVALS =================
  // 1. Camera Frame Loop
  useEffect(() => {
    let interval;
    if (isCameraRunning && tab !== "guide") {
      interval = setInterval(() => {
        processFrame();
      }, 600);
    }
    return () => clearInterval(interval);
  }, [isCameraRunning, tab, processFrame]);

  // 2. Hidden 5-Second Quiz Timer Loop
  useEffect(() => {
    const timerInterval = setInterval(() => {
      if (tabRef.current === "quiz" && quizActiveRef.current) {
        // Only run the timeout check if the hand has actually entered the frame
        if (handDetectedRef.current && quizStartTimeRef.current > 0) {
          if (Date.now() - quizStartTimeRef.current >= 5000) {
            progressQuiz(false); // Time is up! Skip automatically.
          }
        }
      }
    }, 500);

    return () => clearInterval(timerInterval);
  }, [progressQuiz]);

  // ================= KEYBOARD =================
  useEffect(() => {
    const handleKey = (e) => {
      if (tabRef.current !== "sentence") return;

      if (e.key === " ") {
        setSentence((prev) => prev + " ");
        lastAddedRef.current = ""; 
      } else if (e.key === "Backspace") {
        setSentence((prev) => prev.slice(0, -1));
        lastAddedRef.current = ""; 
      }
    };

    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  // ================= UI RENDER =================
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

      <div 
        className="center" 
        style={{ display: tab === "guide" ? "none" : "flex" }}
      >
        <div className="camera-container">
          <video ref={videoRef} autoPlay playsInline muted />
          {!isCameraRunning && (
            <div className="camera-placeholder">
              <button className="btn" onClick={startCamera}>
                Start Camera
              </button>
            </div>
          )}
        </div>
        {isCameraRunning && (
          <h3 className="live-pred">Live: {prediction || "..."}</h3>
        )}
      </div>

      {/* GUIDE */}
      {tab === "guide" && (
        <div className="grid">
          {LETTERS.map((l) => (
            <div key={l} className="card">
              <img src={`/data/guide_images/Sign_language_${l}.png`} alt={`Sign ${l}`} />
              <p>{l}</p>
            </div>
          ))}
        </div>
      )}

      {/* PREDICT */}
      {tab === "predict" && (
        <div className="center mt-20">
          <h2 className="output">Result: {prediction || "Show a sign"}</h2>
        </div>
      )}

      {/* QUIZ */}
      {tab === "quiz" && (
        <div className="center mt-20">
          {!quizActiveRef.current && total < MAX_Q ? (
            <button className="btn blue" onClick={startQuiz}>
              Start 30-Question Quiz
            </button>
          ) : total >= MAX_Q ? (
            <div className="result-card">
              <h2>Quiz Complete!</h2>
              <h1 className="score-text">{score} / {MAX_Q}</h1>
              <button className="btn blue" onClick={startQuiz}>Play Again</button>
            </div>
          ) : (
            <div className="quiz-active">
              <h2>Form the letter:</h2>
              <h1 className="target-letter">{target}</h1>
              <p>Question: {total + 1} / {MAX_Q} | Score: {score}</p>
              <button className="btn red" onClick={() => progressQuiz(false)}>
                Skip Letter
              </button>
            </div>
          )}
        </div>
      )}

      {/* SENTENCE */}
      {tab === "sentence" && (
        <div className="center mt-20">
          <div className="sentence-box">
            <h2 className="sentence">{sentence}</h2>
            {!sentence && <span className="placeholder-text">Begin signing to type...</span>}
          </div>
          <p className="hint">
            Hold sign to type • Press <strong>SPACE</strong> for gap • Press <strong>BACKSPACE</strong> to delete
          </p>
          <button className="btn red" onClick={() => {
            setSentence("");
            lastAddedRef.current = "";
          }}>
            Clear Sentence
          </button>
        </div>
      )}
    </div>
  );
}

export default App;