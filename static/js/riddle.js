// Riddle Master Mini Game JavaScript
document.addEventListener("DOMContentLoaded", () => {
  const wrap = document.querySelector(".riddle-wrap");
  if (!wrap) return;

  const riddleId = Number(wrap.getAttribute("data-riddle-id"));
  const form = document.querySelector(".riddle-answer-form");
  const input = document.querySelector("#guess");
  const result = document.querySelector("#result");
  const prevLink = document.querySelector("#prevLink");
  const nextLink = document.querySelector("#nextLink");
  const revealBtn = document.querySelector("#revealBtn");

  // ---- Challenge Gate ----
  const gate = document.getElementById("challengeGate");
  if (gate && !localStorage.getItem("rm_gate_done")) {
    gate.hidden = false;

    const msg = gate.querySelector(".gate-msg");
    const yesBtn = gate.querySelector("[data-yes]");
    const noBtn = gate.querySelector("[data-no]");

    const say = (text) => {
      if (msg) { msg.textContent = text; }
    };

    yesBtn.addEventListener("click", () => {
      say("Well then—riddle me this.");
      localStorage.setItem("rm_gate_done", "1");
      setTimeout(() => {
        gate.classList.add("hide");
        setTimeout(() => {
          gate.remove();
          // Focus the answer box to "start" the riddle
          if (input) input.focus();
        }, 260);
      }, 800);
    });

    noBtn.addEventListener("click", () => {
      say("Well then—maybe next time.");
      // Turn No button into a Back button after message
      setTimeout(() => {
        noBtn.textContent = "Back";
        // Send them to the riddle list page
        noBtn.addEventListener("click", () => { window.location.href = "/riddle"; }, { once: true });
        // Remove the Yes button to avoid confusion
        yesBtn.remove();
      }, 400);
    });
  }

  // Load neighbors for Prev/Next buttons
  fetch(`/riddle/api/${riddleId}/neighbors`)
    .then(r => r.json())
    .then(data => {
      if (!data.ok) return;
      if (data.prev_id) {
        prevLink.style.display = 'inline-flex';
        prevLink.href = `/riddle/${data.prev_id}`;
      }
      if (data.next_id) {
        nextLink.style.display = 'inline-flex';
        nextLink.href = `/riddle/${data.next_id}`;
      }
    })
    .catch(() => { /* silent */ });

  // Answer submission
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const guess = input.value.trim();
    if (!guess) {
      showResult("Please enter a guess first.", "error");
      return;
    }

    try {
      const res = await fetch(`/riddle/api/${riddleId}/check`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content')
        },
        credentials: 'include',
        body: JSON.stringify({ guess })
      });

      const data = await res.json();

      if (!data.ok) {
        showResult(data.error || "Something went wrong.", "error");
        return;
      }

      if (data.correct) {
        showResult("✅ Correct! Great job. Use Next → to continue or try another riddle.", "success");
        input.value = ""; // Clear input on correct answer
      } else {
        showResult("❌ Not quite right. Try another phrasing or check the hint!", "error");
      }
    } catch (err) {
      console.error('Riddle check error:', err);
      showResult("Network error. Please try again.", "error");
    }
  });

  // Reveal answer functionality
  if (revealBtn) {
    revealBtn.addEventListener("click", async (e) => {
      e.preventDefault();

      // Confirm before spending credits
      if (!confirm("Reveal the answer for 5 credits?")) {
        return;
      }

      // Disable button to prevent double-clicks
      revealBtn.disabled = true;
      revealBtn.textContent = "Revealing...";

      try {
        const res = await fetch(`/riddle/api/${riddleId}/reveal`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            'X-CSRFToken': document.querySelector('meta[name=csrf-token]')?.getAttribute('content')
          },
          credentials: 'include'
        });

        const data = await res.json();

        if (!data.ok) {
          if (data.error === "INSUFFICIENT_CREDITS") {
            showResult(`❌ Insufficient credits! You need ${data.required} credits to reveal the answer.`, "error");
          } else {
            showResult(data.error || "Failed to reveal answer.", "error");
          }
          // Re-enable button on error
          revealBtn.disabled = false;
          revealBtn.textContent = "💡 Reveal Answer (5 credits)";
          return;
        }

        // Show the revealed answer
        showResult(`💡 Answer revealed: "${data.answer}" (${data.cost} credits used)`, "success");

        // Update button to show it was used
        revealBtn.style.display = "none";

        // Optionally fill the input with the answer
        if (input) {
          input.value = data.answer;
          input.disabled = true;
        }

      } catch (err) {
        console.error('Reveal error:', err);
        showResult("Network error. Please try again.", "error");
        // Re-enable button on error
        revealBtn.disabled = false;
        revealBtn.textContent = "💡 Reveal Answer (5 credits)";
      }
    });
  }

  function showResult(msg, type) {
    result.textContent = msg;
    result.style.display = 'block';
    result.classList.remove("success", "error");
    if (type) {
      result.classList.add(type);
    }

    // Auto-hide error messages after 5 seconds
    if (type === "error") {
      setTimeout(() => {
        result.style.display = 'none';
      }, 5000);
    }
  }

  // Focus input on page load
  if (input) {
    input.focus();
  }
});