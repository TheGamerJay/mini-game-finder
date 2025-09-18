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