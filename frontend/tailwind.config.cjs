/** Tailwind config with Outdaxius palette */
module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        admin:   "#2C3E50",
        guide:   "#F39C12",
        traveler:"#3498DB",
        success: "#1E8449",
        danger:  "#E74C3C",
        neutral: "#95A5A6",
        snow:    "#FFFFFF"
      }
    }
  },
  plugins: [],
};
