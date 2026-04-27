import React, { useRef, useState, useEffect, useCallback } from "react";
import "./App.css";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const WORDS = ["HELLO", "WORLD", "APPLE", "REACT", "SIGN", "WATER", "PLEASE", "THANK"];
// UPDATED: Matched exactly to your dataset folder names
const PHRASES = ["Thank you", "Welcome", "Yes", "No", "Help", "Sorry", "Eat", "Hello", "Bye", "Stop"];
const MAX_Q = 30;
const DOUBLE_LETTER_COOLDOWN = 3000; 

function App() {
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]); 
  const tabRef = useRef("predict");

  const stableCharRef = useRef("");
  const stableCountRef = useRef(0);
  const lastAddedRef = useRef("");
  const handDetectedRef = useRef(false);
  const lastAddedTimeRef = useRef(0); 

  const quizActiveRef = useRef(false);
  const quizTargetRef = useRef("");
  const quizStartTimeRef = useRef(0);

  const wordActiveRef = useRef(false);
  const targetWordRef = useRef("");
  const wordIndexRef = useRef(0);
  const wordStartTimeRef = useRef(0);
  const wordHandDetectedRef = useRef(false);

  const phraseTargetRef = useRef("");

  const [tab, setTabState] = useState("predict");
  const [prediction, setPrediction] = useState("");
  const [isCameraRunning, setIsCameraRunning] = useState(false);
  const [isRecording, setIsRecording] = useState(false); 

  const [sentence, setSentence] = useState("");
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [target, setTarget] = useState("");
  const [quizStats, setQuizStats] = useState([]); 

  const [word, setWord] = useState("");
  const [wordProgress, setWordProgress] = useState(0);
  const [wordResults, setWordResults] = useState([]); 
  const [wordComplete, setWordComplete] = useState(false);

  const [phrase, setPhrase] = useState("");
  const [phraseComplete, setPhraseComplete] = useState(false);

  const setTab = (newTab) => {
    setTabState(newTab);
    tabRef.current = newTab;
    setPrediction("");
  };

  const speakSentence = () => {
    if (!sentence) return;
    const utterance = new SpeechSynthesisUtterance(sentence);
    utterance.rate = 0.9; 
    window.speechSynthesis.speak(utterance);
  };

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

  const recordAndPredictSequence = useCallback(() => {
    if (!videoRef.current || !videoRef.current.srcObject) return;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") return;

    setIsRecording(true);
    recordedChunksRef.current = [];

    const stream = videoRef.current.srcObject;
    const mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorderRef.current = mediaRecorder;

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        recordedChunksRef.current.push(e.data);
      }
    };

    mediaRecorder.onstop = async () => {
      setIsRecording(false);
      const blob = new Blob(recordedChunksRef.current, { type: "video/webm" });
      const formData = new FormData();
      formData.append("file", blob); 

      try {
        const res = await fetch("http://127.0.0.1:8000/predict_sequence", {
          method: "POST",
          body: formData,
        });
        const data = await res.json();
        const currentPred = data.label ? data.label.trim() : "";
        
        setPrediction(currentPred);

        if (tabRef.current === "phrases" && currentPred === phraseTargetRef.current && !phraseComplete) {
            setPhraseComplete(true);
        }

      } catch (error) {
        console.error("Sequence Prediction API Error:", error);
      }
    };

    mediaRecorder.start();
    
    // Stop recording after 3000ms (3 seconds) to ensure 60 frames are captured
    setTimeout(() => {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
    }, 3000); 

  }, [phraseComplete]);

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

        if (currentPred) {
          handleAppLogic(currentPred);
        }
      } catch (error) {
        console.error("Static Prediction API Error:", error);
      }
    }, "image/jpeg");
  }, []);

  const handleAppLogic = (currentPred) => {
    const currentTab = tabRef.current;

    if (currentTab === "sentence") {
      if (currentPred === stableCharRef.current) {
        stableCountRef.current += 1;
      } else {
        stableCharRef.current = currentPred;
        stableCountRef.current = 1;
      }

      const isSameAsLast = currentPred === lastAddedRef.current;
      const cooldownPassed = Date.now() - lastAddedTimeRef.current >= DOUBLE_LETTER_COOLDOWN;

      if (stableCountRef.current >= 3 && (!isSameAsLast || cooldownPassed)) {
        if (PHRASES.includes(currentPred)) {
          setSentence((prev) => {
            const prefix = prev.length > 0 && !prev.endsWith(" ") ? " " : "";
            return prev + prefix + currentPred + " ";
          });
        } else {
          setSentence((prev) => prev + currentPred);
        }
        lastAddedRef.current = currentPred;
        lastAddedTimeRef.current = Date.now();
        stableCountRef.current = 0;
      }
    }

    if (currentTab === "quiz" && quizActiveRef.current) {
      if (!handDetectedRef.current) {
        handDetectedRef.current = true;
        quizStartTimeRef.current = Date.now();
      }

      if (currentPred === quizTargetRef.current) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= 2) progressQuiz(true);
      } else {
        stableCountRef.current = 0;
      }
    }

    if (currentTab === "word" && wordActiveRef.current && !wordComplete) {
      if (!wordHandDetectedRef.current) {
        wordHandDetectedRef.current = true;
        wordStartTimeRef.current = Date.now();
      }

      const currentTargetLetter = targetWordRef.current[wordIndexRef.current];

      if (currentPred === currentTargetLetter) {
        stableCountRef.current += 1;
        if (stableCountRef.current >= 2) progressWord(true);
      } else {
        stableCountRef.current = 0;
      }
    }
  };

  const startPhraseMode = () => {
    const randomPhrase = PHRASES[Math.floor(Math.random() * PHRASES.length)];
    setPhrase(randomPhrase);
    phraseTargetRef.current = randomPhrase;
    setPhraseComplete(false);
  };
  
  const progressWord = useCallback((isCorrect) => {
    setWordResults((prev) => [...prev, isCorrect]);
    wordIndexRef.current += 1;
    setWordProgress(wordIndexRef.current);
    stableCountRef.current = 0;
    wordHandDetectedRef.current = false;
    wordStartTimeRef.current = 0;

    if (wordIndexRef.current >= targetWordRef.current.length) {
      wordActiveRef.current = false;
      setWordComplete(true);
    }
  }, []);

  const startWordMode = () => {
    const randomWord = WORDS[Math.floor(Math.random() * WORDS.length)];
    setWord(randomWord);
    targetWordRef.current = randomWord;
    setWordProgress(0);
    setWordResults([]);
    wordIndexRef.current = 0;
    setWordComplete(false);
    wordActiveRef.current = true;
    stableCountRef.current = 0;
    wordHandDetectedRef.current = false;
    wordStartTimeRef.current = 0;
  };

  const progressQuiz = useCallback((isCorrect) => {
    const timeTaken = handDetectedRef.current 
      ? ((Date.now() - quizStartTimeRef.current) / 1000).toFixed(1) 
      : 0;

    setQuizStats((prev) => [...prev, { letter: quizTargetRef.current, correct: isCorrect, time: isCorrect ? timeTaken : "Wrong" }]);
    if (isCorrect) setScore((s) => s + 1);

    setTotal((prevTotal) => {
      const newTotal = prevTotal + 1;
      if (newTotal >= MAX_Q) {
        quizActiveRef.current = false;
        return newTotal;
      }
      const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
      setTarget(randomLetter);
      quizTargetRef.current = randomLetter;
      stableCountRef.current = 0;
      handDetectedRef.current = false;
      quizStartTimeRef.current = 0; 
      return newTotal;
    });
  }, []);

  const startQuiz = () => {
    setScore(0);
    setTotal(0);
    setQuizStats([]); 
    quizActiveRef.current = true;
    const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
    setTarget(randomLetter);
    quizTargetRef.current = randomLetter;
    stableCountRef.current = 0;
    handDetectedRef.current = false;
    quizStartTimeRef.current = 0;
  };

  // ================= INTERVALS =================
  useEffect(() => {
    let interval;
    if (isCameraRunning && tab !== "guide") {
      if (tab === "phrases") {
        interval = setInterval(() => {
          recordAndPredictSequence();
        }, 3500); 
      } else {
        interval = setInterval(() => {
          processFrame();
        }, 600);
      }
    }
    return () => {
        clearInterval(interval);
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
            mediaRecorderRef.current.stop();
        }
    }
  }, [isCameraRunning, tab, processFrame, recordAndPredictSequence]);

  useEffect(() => {
    const timerInterval = setInterval(() => {
      const now = Date.now();
      if (tabRef.current === "quiz" && quizActiveRef.current) {
        if (handDetectedRef.current && quizStartTimeRef.current > 0) {
          if (now - quizStartTimeRef.current >= 5000) progressQuiz(false); 
        }
      }
      if (tabRef.current === "word" && wordActiveRef.current && !wordComplete) {
        if (wordHandDetectedRef.current && wordStartTimeRef.current > 0) {
          if (now - wordStartTimeRef.current >= 5000) progressWord(false); 
        }
      }
    }, 500);
    return () => clearInterval(timerInterval);
  }, [progressQuiz, progressWord, wordComplete]);

  useEffect(() => {
    const handleKey = (e) => {
      if (tabRef.current !== "sentence") return;
      if (e.key === " ") {
        setSentence((prev) => prev + " ");
        lastAddedRef.current = ""; 
        lastAddedTimeRef.current = 0;
      } else if (e.key === "Backspace") {
        setSentence((prev) => prev.slice(0, -1));
        lastAddedRef.current = ""; 
        lastAddedTimeRef.current = 0;
      }
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, []);

  const renderAnalytics = () => {
    const correctAnswers = quizStats.filter(s => s.correct);
    const fastest = correctAnswers.length > 0 ? correctAnswers.reduce((min, p) => parseFloat(p.time) < parseFloat(min.time) ? p : min, correctAnswers[0]) : null;
    const slowest = correctAnswers.length > 0 ? correctAnswers.reduce((max, p) => parseFloat(p.time) > parseFloat(max.time) ? p : max, correctAnswers[0]) : null;

    return (
      <div className="analytics-container">
        <h3>📊 Post-Quiz Analytics</h3>
        <div className="stats-highlight">
          <p><strong>Fastest Sign:</strong> {fastest ? `${fastest.letter} (${fastest.time}s)` : "N/A"}</p>
          <p><strong>Slowest Sign:</strong> {slowest ? `${slowest.letter} (${slowest.time}s)` : "N/A"}</p>
        </div>
        <div className="stats-table-container">
          <table className="stats-table">
            <thead>
              <tr><th>Q#</th><th>Letter</th><th>Result</th><th>Time</th></tr>
            </thead>
            <tbody>
              {quizStats.map((stat, i) => (
                <tr key={i} className={stat.correct ? "row-correct" : "row-wrong"}>
                  <td>{i + 1}</td><td>{stat.letter}</td><td>{stat.correct ? "✅" : "❌"}</td><td>{stat.time}{stat.correct ? "s" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      <h1 className="title">🤟 AI Sign Language Tutor</h1>

      <div className="tabs">
        {["guide", "predict", "quiz", "word", "phrases", "sentence"].map((t) => (
          <button key={t} className={`tab ${tab === t ? "active" : ""}`} onClick={() => setTab(t)}>
            {t.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="center" style={{ display: tab === "guide" ? "none" : "flex" }}>
        <div className="camera-container">
          <video ref={videoRef} autoPlay playsInline muted />
          {!isCameraRunning && (
            <div className="camera-placeholder">
              <button className="btn" onClick={startCamera}>Start Camera</button>
            </div>
          )}
        </div>
        {isCameraRunning && (
            <h3 className="live-pred">
                Live: {prediction || "..."} 
                {isRecording && <span style={{color: 'red', marginLeft: '10px', fontSize: '0.8em'}}>⏺ Recording...</span>}
            </h3>
        )}
      </div>

      {tab === "guide" && (
        <div className="guide-container" style={{ padding: "20px", maxWidth: "900px", margin: "0 auto" }}>
          <h2 style={{ textAlign: "left", color: "#3b82f6", borderBottom: "2px solid #334155", paddingBottom: "10px" }}>Common Phrases</h2>
          <div className="grid">
            {PHRASES.map((p) => (
              <div key={p} className="card">
                {/* Ensure your images in public/data/guide_images/ match this exact casing, e.g., Eat.png */}
                <img src={`/data/guide_images/${p.replace(/ /g, "_")}.png`} alt={`Sign ${p}`} onError={(e) => { e.target.src = "/data/guide_images/placeholder.png"; }} />
                <p style={{ fontWeight: "bold", fontSize: "1.2rem", color: "#facc15" }}>{p}</p>
              </div>
            ))}
          </div>
          <h2 style={{ textAlign: "left", color: "#3b82f6", borderBottom: "2px solid #334155", paddingBottom: "10px", marginTop: "40px" }}>Alphabet</h2>
          <div className="grid">
            {LETTERS.map((l) => (
              <div key={l} className="card">
                <img src={`/data/guide_images/Sign_language_${l}.png`} alt={`Sign ${l}`} />
                <p>{l}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "predict" && <div className="center mt-20"><h2 className="output">Result: {prediction || "Show a sign"}</h2></div>}

      {tab === "quiz" && (
        <div className="center mt-20">
          {!quizActiveRef.current && total < MAX_Q && total === 0 ? (
            <button className="btn blue" onClick={startQuiz}>Start 30-Question Quiz</button>
          ) : total >= MAX_Q ? (
            <div className="result-card">
              <h2>Quiz Complete!</h2><h1 className="score-text">{score} / {MAX_Q}</h1>{renderAnalytics()}<button className="btn blue" onClick={startQuiz}>Play Again</button>
            </div>
          ) : (
            <div className="quiz-active">
              <h2>Form the letter:</h2><h1 className="target-letter">{target}</h1><p>Question: {total + 1} / {MAX_Q} | Score: {score}</p><button className="btn red" onClick={() => progressQuiz(false)}>Mark as Wrong</button>
            </div>
          )}
        </div>
      )}

      {tab === "word" && (
        <div className="center mt-20">
          {!wordActiveRef.current && !wordComplete ? (
             <button className="btn blue" onClick={startWordMode}>Start Spelling Bee</button>
          ) : wordComplete ? (
            <div className="result-card">
              <h2>Word Complete!</h2>
              <div className="word-display mt-20">
                {word.split("").map((char, i) => (<span key={i} className={`word-char ${wordResults[i] ? "completed" : "wrong"}`}>{char}</span>))}
              </div>
              <button className="btn blue mt-20" onClick={startWordMode}>Next Word</button>
            </div>
          ) : (
            <div className="word-active">
              <h2>Spell the word:</h2>
              <div className="word-display">
                {word.split("").map((char, i) => {
                  let statusClass = "";
                  if (i === wordProgress) statusClass = "current";
                  else if (i < wordProgress) { statusClass = wordResults[i] ? "completed" : "wrong"; }
                  return (<span key={i} className={`word-char ${statusClass}`}>{char}</span>);
                })}
              </div>
              <p className="hint mt-20">You have 5 seconds per letter!</p>
            </div>
          )}
        </div>
      )}

      {tab === "phrases" && (
        <div className="center mt-20">
          {!phrase ? (
             <button className="btn blue" onClick={startPhraseMode}>Practice Phrases</button>
          ) : phraseComplete ? (
            <div className="result-card">
              <h2>Awesome! You signed:</h2>
              <h1 className="target-letter" style={{ fontSize: "2.5rem", color: "#22c55e" }}>{phrase}</h1>
              <button className="btn blue mt-20" onClick={startPhraseMode}>Next Phrase</button>
            </div>
          ) : (
            <div className="phrase-active">
              <h2>Sign the phrase:</h2>
              <h1 className="target-letter" style={{ fontSize: "3rem" }}>{phrase}</h1>
              <p className="hint mt-20">Perform the action over the next 2 seconds.</p>
            </div>
          )}
        </div>
      )}

      {tab === "sentence" && (
        <div className="center mt-20">
          <div className="sentence-box"><h2 className="sentence">{sentence}</h2>{!sentence && <span className="placeholder-text">Begin signing to type...</span>}</div>
          <p className="hint">Hold sign to type • Cooldown for double letters: {DOUBLE_LETTER_COOLDOWN / 1000}s</p>
          <div className="button-group">
            <button className="btn blue" onClick={speakSentence} disabled={!sentence}>🗣️ Speak</button>
            <button className="btn red" onClick={() => { setSentence(""); lastAddedRef.current = ""; lastAddedTimeRef.current = 0;}}>Clear</button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;