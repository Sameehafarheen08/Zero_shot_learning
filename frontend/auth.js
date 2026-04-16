// Global logout function for all pages
function handleLogout(event) {
  if (event) event.preventDefault();
  if (confirm("Are you sure you want to logout?")) {
    // Clear all session data
    sessionStorage.clear();
    localStorage.clear();
    
    // Optional: Notify backend
    fetch("http://localhost:5000/api/auth/logout", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${sessionStorage.getItem("token") || ""}`
      }
    }).catch(e => console.log("Logout notification sent"));
    
    // Redirect to login
    window.location.href = "login.html";
  }
}

// Check user role and redirect if needed
function checkAuthAndRole() {
  const userId = sessionStorage.getItem("user_id");
  const isAdmin = sessionStorage.getItem("is_admin") === "true";
  const currentPage = window.location.pathname;
  
  // If not logged in, redirect to login
  if (!userId) {
    if (!currentPage.includes("login.html") && !currentPage.includes("signup.html")) {
      window.location.href = "login.html";
    }
    return;
  }
  
  // If admin trying to access user pages - allow but warn
  // If user trying to access admin pages - block
  if (currentPage.includes("admin") && !isAdmin) {
    alert("Admin access required!");
    window.location.href = "index.html";
  }
}

// Run auth check on page load
document.addEventListener("DOMContentLoaded", checkAuthAndRole);
