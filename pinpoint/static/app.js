const query = document.querySelector('#query');
const clear = document.querySelector('#clear-search');
if (query && clear) {
  query.addEventListener('input', () => { clear.hidden = !query.value; });
  clear.addEventListener('click', () => {
    query.value = '';
    query.focus();
    query.form.requestSubmit();
  });
  clear.disabled = false;
}
const printBrief = document.querySelector('#print-brief');
if (printBrief) {
  printBrief.addEventListener('click', () => window.print());
  printBrief.disabled = false;
}
