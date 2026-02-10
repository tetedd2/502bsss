const video = document.getElementById("camera");
let stream=null,running=false;

const canvas=document.createElement("canvas");
const ctx=canvas.getContext("2d");

async function startCamera(){
stream=await navigator.mediaDevices.getUserMedia({video:true});
video.srcObject=stream;
running=true;
loop();
}

function stopCamera(){
running=false;
if(stream) stream.getTracks().forEach(t=>t.stop());
}

async function loop(){
while(running){
await capture("/detect");
await new Promise(r=>setTimeout(r,1500));
}
}

async function capture(url){
canvas.width=video.videoWidth;
canvas.height=video.videoHeight;
ctx.drawImage(video,0,0);

const blob=await new Promise(r=>canvas.toBlob(r,"image/jpeg"));
const f=new FormData();
f.append("image",blob);

return fetch(url,{method:"POST",body:f});
}

async function registerFace(){
const name=document.getElementById("reg-name").value;
if(!name) return alert("Enter name");

canvas.width=video.videoWidth;
canvas.height=video.videoHeight;
ctx.drawImage(video,0,0);

const blob=await new Promise(r=>canvas.toBlob(r,"image/jpeg"));

const f=new FormData();
f.append("image",blob);
f.append("name",name);

await fetch("/register",{method:"POST",body:f});
alert("Registered!");
}

async function loadUsers(){
const res=await fetch("/stats");
const data=await res.json();

document.getElementById("count").innerText=data.violations;

const div=document.getElementById("user-list");
div.innerHTML="";

data.users.forEach(u=>{
div.innerHTML+=`<p>${u.name} : ${u.score}</p>`;
});
}

setInterval(loadUsers,2000);

function showPage(p){
["live","register","dashboard"].forEach(x=>{
document.getElementById("page-"+x).style.display="none";
});
document.getElementById("page-"+p).style.display="block";
}

document.getElementById("btn-start").onclick=startCamera;
document.getElementById("btn-stop").onclick=stopCamera;
