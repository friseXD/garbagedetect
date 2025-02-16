window.onload = () => {
  $("#sendbutton").click(() => {
    $("#link").css("visibility", "visible");
    $("#download").attr("href", "static/");
  });
};

function readUrl(input) {
  imagebox = $("#imagebox");
  console.log(imagebox);
  console.log("evoked readUrl");
  if (input.files && input.files[0]) {
    let reader = new FileReader();
    reader.onload = function (e) {
      console.log(e.target);

      imagebox.attr("src", e.target.result);
      imagebox.height(500);
      imagebox.width(800);
    };
    reader.readAsDataURL(input.files[0]);
  }
}

document.addEventListener("DOMContentLoaded", function () {
  // Находим все формы на странице
  const forms = document.querySelectorAll("form");

  forms.forEach(form => {
      form.addEventListener("submit", function () {
          // Показываем анимацию загрузки
          const overlay = document.createElement("div");
          overlay.className = "overlay";

          const loader = document.createElement("div");
          loader.className = "loader";

          overlay.appendChild(loader);
          document.body.appendChild(overlay);

          // Показываем overlay и loader
          overlay.style.display = "flex";
      });
  });
});