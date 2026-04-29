import React, { useRef, useState, useEffect, useCallback } from "react";
import "./App.css";

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");
const PHRASES = ["Thank you", "Welcome", "Yes", "No", "Help", "Sorry", "Eat", "Hello", "Bye", "Stop"];
const MAX_Q = 30;
const DOUBLE_LETTER_COOLDOWN = 3000; 

const FALLBACK_WORDS = ["APPLE", "WATER", "SMILE", "HAPPY", "GREEN", "PLANT", "TIGER", "RIVER", "CLOUD", "BRAIN", "LIGHT", "MUSIC", "WORLD", "HELLO"];

const fetchRandomWord = async () => {
  try {
    const res = await fetch(`https://random-word-api.herokuapp.com/word`);
    if (!res.ok) throw new Error("API Network error");
    const data = await res.json();
    return data[0].toUpperCase();
  } catch (err) {
    console.warn("Using fallback word list due to API error.");
    return FALLBACK_WORDS[Math.floor(Math.random() * FALLBACK_WORDS.length)];
  }
};

function App() {
  const videoRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]); 
  
  // NEW: Sidebar Layout State
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const [tab, setTabState] = useState("home");
  const tabRef = useRef("home");

  // --- LOCAL STORAGE: USER AUTH ---
  const [user, setUser] = useState(() => {
    const savedUser = localStorage.getItem('signLanguageTutorUser');
    return savedUser ? JSON.parse(savedUser) : null;
  });
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // --- LOCAL STORAGE: ANALYTICS ---
  const [quizStats, setQuizStats] = useState(() => {
    const savedStats = localStorage.getItem('signLanguageStats');
    return savedStats ? JSON.parse(savedStats) : [];
  });

  useEffect(() => {
    localStorage.setItem('signLanguageStats', JSON.stringify(quizStats));
  }, [quizStats]);

  // Shared Logic Refs
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

  const phraseActiveRef = useRef(false);
  const phraseTargetRef = useRef("");
  const phraseStartTimeRef = useRef(0);
  const phraseHandDetectedRef = useRef(false);

  const [prediction, setPrediction] = useState("");
  const [isCameraRunning, setIsCameraRunning] = useState(false);
  const [isRecording, setIsRecording] = useState(false); 

  const [sentence, setSentence] = useState("");
  const [score, setScore] = useState(0);
  const [total, setTotal] = useState(0);
  const [target, setTarget] = useState("");

  const [word, setWord] = useState("");
  const [wordProgress, setWordProgress] = useState(0);
  const [wordResults, setWordResults] = useState([]); 
  const [wordComplete, setWordComplete] = useState(false);
  const [isFetchingWord, setIsFetchingWord] = useState(false);

  const [phrase, setPhrase] = useState("");
  const [phraseResult, setPhraseResult] = useState(null); 

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
    if (tabRef.current === "phrases" && !phraseActiveRef.current) return;
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
        
        if (tabRef.current === "phrases" && phraseActiveRef.current) {
          if (!phraseHandDetectedRef.current) {
            phraseHandDetectedRef.current = true;
            phraseStartTimeRef.current = Date.now();
          }
          
          const currentPred = data.label ? data.label.trim() : "";
          setPrediction(currentPred);

          if (currentPred === phraseTargetRef.current) {
            phraseActiveRef.current = false;
            setPhraseResult('correct');
          }
        }
      } catch (error) {
        console.error("Sequence Prediction API Error:", error);
      }
    };

    mediaRecorder.start();
    setTimeout(() => {
      if (mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
    }, 3000); 
  }, []);

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
        if (currentPred) handleAppLogic(currentPred);
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
    setPhraseResult(null);
    phraseActiveRef.current = true;
    phraseStartTimeRef.current = 0;
    phraseHandDetectedRef.current = false;
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

  const startWordMode = async () => {
    setIsFetchingWord(true);
    const dynamicWord = await fetchRandomWord();
    setWord(dynamicWord);
    targetWordRef.current = dynamicWord;
    setWordProgress(0);
    setWordResults([]);
    wordIndexRef.current = 0;
    setWordComplete(false);
    wordActiveRef.current = true;
    stableCountRef.current = 0;
    wordHandDetectedRef.current = false;
    wordStartTimeRef.current = 0;
    setIsFetchingWord(false);
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
    quizActiveRef.current = true;
    const randomLetter = LETTERS[Math.floor(Math.random() * LETTERS.length)];
    setTarget(randomLetter);
    quizTargetRef.current = randomLetter;
    stableCountRef.current = 0;
    handDetectedRef.current = false;
    quizStartTimeRef.current = 0;
  };

  // ================= INTERVALS & TIMERS =================
  useEffect(() => {
    let interval;
    const noCameraTabs = ["home", "login", "dashboard", "guide"];
    if (isCameraRunning && !noCameraTabs.includes(tab)) {
      if (tab === "phrases") {
        interval = setInterval(() => recordAndPredictSequence(), 3500); 
      } else {
        interval = setInterval(() => processFrame(), 600);
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
      if (tabRef.current === "phrases" && phraseActiveRef.current) {
        if (phraseHandDetectedRef.current && phraseStartTimeRef.current > 0) {
          if (now - phraseStartTimeRef.current >= 10000) { 
            phraseActiveRef.current = false;
            setPhraseResult('wrong');
          }
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
              {[...quizStats].reverse().map((stat, i) => (
                <tr key={i} className={stat.correct ? "row-correct" : "row-wrong"}>
                  <td>{quizStats.length - i}</td><td>{stat.letter}</td><td>{stat.correct ? "✅" : "❌"}</td><td>{stat.time}{stat.correct ? "s" : ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  };

  const handleLogout = () => {
    setUser(null); 
    setTab("home");
    localStorage.removeItem('signLanguageTutorUser'); 
  };

  const hideCameraTabs = ["home", "login", "dashboard", "guide"];

  return (
    <div className="app-layout">
      
      {/* TOP NAVIGATION BAR */}
      <header className="topbar">
        <div className="topbar-left">
          <button className="icon-btn" onClick={() => setIsSidebarOpen(!isSidebarOpen)}>
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="3" y1="12" x2="21" y2="12"></line>
              <line x1="3" y1="6" x2="21" y2="6"></line>
              <line x1="3" y1="18" x2="21" y2="18"></line>
            </svg>
          </button>
          <span className="brand-logo" onClick={() => setTab("home")}>SignTutor</span>
        </div>
        
        <div className="topbar-right">
          {user ? (
            <div className="user-profile-nav">
              <div className="avatar">{user.name.charAt(0).toUpperCase()}</div>
              <span className="user-name">{user.name}</span>
              <button className="btn-outline red" onClick={handleLogout}>Logout</button>
            </div>
          ) : (
            <button className="btn primary" onClick={() => setTab("login")}>Log In</button>
          )}
        </div>
      </header>

      {/* MAIN CONTENT AREA WITH SIDEBAR */}
      <div className="main-container">
        
        {/* COLLAPSIBLE LEFT SIDEBAR */}
        <aside className={`sidebar ${isSidebarOpen ? "open" : "closed"}`}>
          <nav className="sidebar-nav">
            <button className={`nav-item ${tab === "home" ? "active" : ""}`} onClick={() => setTab("home")}>Home</button>
            
            {/* Dashboard only visible if logged in */}
            {user && (
              <button className={`nav-item highlight ${tab === "dashboard" ? "active" : ""}`} onClick={() => setTab("dashboard")}>Dashboard</button>
            )}
            
            <div className="nav-section-title">Learn</div>
            <button className={`nav-item ${tab === "guide" ? "active" : ""}`} onClick={() => setTab("guide")}>Dictionary Guide</button>
            
            <div className="nav-section-title">Practice</div>
            <button className={`nav-item ${tab === "predict" ? "active" : ""}`} onClick={() => setTab("predict")}>Free Practice</button>
            <button className={`nav-item ${tab === "quiz" ? "active" : ""}`} onClick={() => setTab("quiz")}>Alphabet Quiz</button>
            <button className={`nav-item ${tab === "word" ? "active" : ""}`} onClick={() => setTab("word")}>Spelling Bee</button>
            <button className={`nav-item ${tab === "phrases" ? "active" : ""}`} onClick={() => setTab("phrases")}>Real Phrases</button>
            <button className={`nav-item ${tab === "sentence" ? "active" : ""}`} onClick={() => setTab("sentence")}>Sentence Typer</button>
          </nav>
        </aside>

        {/* SCROLLABLE CONTENT AREA */}
        <main className="content-area">
          <div className="content-wrapper">

            {tab === "home" && (
              <div className="view-container">
                <h1 className="hero-title">Master Sign Language with AI</h1>
                <p className="hero-subtitle">
                  Practice the alphabet, test your spelling speed, and learn real-world phrases with instant, real-time feedback powered by neural networks.
                </p>
                <div className="button-group">
                  <button className="btn primary lg" onClick={() => setTab(user ? "dashboard" : "login")}>
                    {user ? "Go to Dashboard" : "Get Started"}
                  </button>
                  <button className="btn outline lg" onClick={() => setTab("guide")}>View Dictionary</button>
                </div>
              </div>
            )}

            {tab === "login" && (
              <div className="view-container">
                <div className="panel login-panel">
                  <h2>Welcome Back</h2>
                  <p className="subtitle">Sign in to track your progress</p>
                  
                  <div className="form-group">
                    <label>Email Address</label>
                    <input 
                      type="email" 
                      value={loginEmail}
                      onChange={(e) => setLoginEmail(e.target.value)}
                      placeholder="name@example.com"
                    />
                  </div>
                  <div className="form-group">
                    <label>Password (Demo: Any)</label>
                    <input 
                      type="password" 
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••"
                    />
                  </div>
                  <button 
                    className="btn primary full-width" 
                    onClick={() => {
                      if(loginEmail.includes("@")) {
                        const newUser = { email: loginEmail, name: loginEmail.split("@")[0] };
                        setUser(newUser);
                        setTab("dashboard");
                        localStorage.setItem('signLanguageTutorUser', JSON.stringify(newUser));
                      } else {
                        alert("Please enter a valid email to test the login.");
                      }
                    }}
                  >
                    Continue
                  </button>
                </div>
              </div>
            )}

            {tab === "dashboard" && user && (
              <div className="view-container align-left">
                <div className="dashboard-header">
                  <div>
                    <h2 className="section-title">Hello, {user.name}</h2>
                    <p className="subtitle">Here is your learning progress.</p>
                  </div>
                  <div className="badge success">Active Learner</div>
                </div>

                <div className="metrics-grid">
                  <div className="metric-card">
                    <span className="metric-label">Questions Answered</span>
                    <span className="metric-value">{quizStats.length}</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Total Correct</span>
                    <span className="metric-value success">{quizStats.filter(s => s.correct).length}</span>
                  </div>
                  <div className="metric-card">
                    <span className="metric-label">Current Focus</span>
                    <span className="metric-value focus">Alphabet</span>
                  </div>
                </div>

                <div className="panel table-panel">
                  <h3 className="panel-title">Recent Quiz History</h3>
                  {quizStats.length === 0 ? (
                    <div className="empty-state">
                      <p>No practice data available yet.</p>
                      <button className="btn primary" onClick={() => setTab("quiz")}>Start a Quiz</button>
                    </div>
                  ) : (
                    renderAnalytics() 
                  )}
                </div>
              </div>
            )}

            {/* CAMERA SECTION (Hidden on static pages) */}
            <div className="camera-section" style={{ display: hideCameraTabs.includes(tab) ? "none" : "flex" }}>
              <div className="camera-wrapper">
                <video ref={videoRef} autoPlay playsInline muted />
                {!isCameraRunning && (
                  <div className="camera-overlay">
                    <button className="btn primary" onClick={startCamera}>Enable Camera Feed</button>
                  </div>
                )}
              </div>
              {isCameraRunning && (
                <div className="live-status">
                  <span className="status-indicator"></span>
                  Live Translation: <strong>{prediction || "Waiting for sign..."}</strong>
                  {isRecording && <span className="recording-badge">Recording sequence</span>}
                </div>
              )}
            </div>

            {/* LEARNING/PRACTICE VIEWS */}
            {tab === "guide" && (
              <div className="view-container align-left">
                <h2 className="section-title">Common Phrases</h2>
                <div className="dictionary-grid">
                  {PHRASES.map((p) => (
                    <div key={p} className="dict-card">
                      <img src={`/data/guide_images/${p.replace(/ /g, "_")}.png`} alt={`Sign ${p}`} onError={(e) => { e.target.src = "/data/guide_images/placeholder.png"; }} />
                      <p>{p}</p>
                    </div>
                  ))}
                </div>
                <h2 className="section-title" style={{ marginTop: "40px" }}>The Alphabet</h2>
                <div className="dictionary-grid">
                  {LETTERS.map((l) => (
                    <div key={l} className="dict-card">
                      <img src={`/data/guide_images/Sign_language_${l}.png`} alt={`Sign ${l}`} />
                      <p>{l}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tab === "predict" && <div className="view-container"><h2 className="section-title">Free Practice Mode</h2><p className="subtitle">Show any sign to the camera to see the translation.</p></div>}

            {tab === "quiz" && (
              <div className="view-container">
                {!quizActiveRef.current && total < MAX_Q && total === 0 ? (
                  <button className="btn primary lg" onClick={startQuiz}>Start Alphabet Quiz</button>
                ) : total >= MAX_Q ? (
                  <div className="panel result-panel">
                    <h2>Quiz Complete</h2>
                    <h1 className="huge-score">{score} / {MAX_Q}</h1>
                    <button className="btn primary mt-20" onClick={startQuiz}>Play Again</button>
                  </div>
                ) : (
                  <div className="panel active-panel">
                    <p className="subtitle">Question {total + 1} of {MAX_Q} — Score: {score}</p>
                    <h1 className="target-display">{target}</h1>
                    <button className="btn outline red mt-20" onClick={() => progressQuiz(false)}>Skip / Mark Wrong</button>
                  </div>
                )}
              </div>
            )}

            {tab === "word" && (
              <div className="view-container">
                {!wordActiveRef.current && !wordComplete ? (
                   <button className="btn primary lg" onClick={startWordMode} disabled={isFetchingWord}>
                     {isFetchingWord ? "Loading..." : "Start Spelling Bee"}
                   </button>
                ) : wordComplete ? (
                  <div className="panel result-panel">
                    <h2>Word Completed</h2>
                    <div className="word-blocks mt-20">
                      {word.split("").map((char, i) => (<span key={i} className={`block ${wordResults[i] ? "success" : "danger"}`}>{char}</span>))}
                    </div>
                    <button className="btn primary mt-20" onClick={startWordMode} disabled={isFetchingWord}>
                      {isFetchingWord ? "Loading..." : "Next Word"}
                    </button>
                  </div>
                ) : (
                  <div className="panel active-panel">
                    <p className="subtitle">5 seconds per letter</p>
                    <div className="word-blocks mt-20">
                      {word.split("").map((char, i) => {
                        let status = "";
                        if (i === wordProgress) status = "current";
                        else if (i < wordProgress) status = wordResults[i] ? "success" : "danger";
                        return (<span key={i} className={`block ${status}`}>{char}</span>);
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}

            {tab === "phrases" && (
              <div className="view-container">
                {!phrase ? (
                   <button className="btn primary lg" onClick={startPhraseMode}>Practice Phrases</button>
                ) : phraseResult === 'correct' ? (
                  <div className="panel result-panel">
                    <h2>Excellent!</h2>
                    <h1 className="target-display success">{phrase}</h1>
                    <button className="btn primary mt-20" onClick={startPhraseMode}>Next Phrase</button>
                  </div>
                ) : phraseResult === 'wrong' ? (
                  <div className="panel result-panel">
                    <h2>Time's Up ⏳</h2>
                    <h1 className="target-display danger">{phrase}</h1>
                    <button className="btn primary mt-20" onClick={startPhraseMode}>Try Another</button>
                  </div>
                ) : (
                  <div className="panel active-panel">
                    <p className="subtitle">You have 10 seconds</p>
                    <h1 className="target-display">{phrase}</h1>
                  </div>
                )}
              </div>
            )}

            {tab === "sentence" && (
              <div className="view-container">
                <div className="panel typer-panel">
                  <h2 className="typed-sentence">{sentence || <span className="placeholder">Start signing to type...</span>}</h2>
                </div>
                <div className="button-group mt-20">
                  <button className="btn primary" onClick={speakSentence} disabled={!sentence}>Speak</button>
                  <button className="btn outline red" onClick={() => { setSentence(""); lastAddedRef.current = ""; lastAddedTimeRef.current = 0;}}>Clear</button>
                </div>
              </div>
            )}

          </div>
        </main>
      </div>
    </div>
  );
}

export default App;