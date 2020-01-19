function signUp(form){
    userid = form.userid.value;
    pswrd = form.pswrd.value;
    return $.ajax({
        type: "POST",
        url: '/api/users',
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        data: JSON.stringify({
            "username": userid, "password": pswrd
        })
    });
}

// This is from the following source https://github.com/yushulx/web-camera-recorder/blob/master/static/recorder.js
async function logIn() {
    /*the following code checkes whether the entered userid and password are matching*/
    // userid = form.userid.value;
    // pswrd = form.pswrd.value;
    // try {
        var token = await $.ajax({
            url: '/api/token',
            // headers: {
            //     "Authorization": userid + ":" + pswrd
            // }
        });
        if (token) {
            onLogIn(token);
        }
        else {
            alert("There was an error logging in, but your username and password may be correct. Please try again");
        }
    // }
    // catch{
    //     await $.ajax({
    //         url: '/api/users',
    //         type: "POST",
    //         data: {
    //             "username": userid, "password": pswrd
    //         }
    //     });
    //     var token = await $.ajax({
    //         url: '/api/token',
    //         headers: {
    //             "Authorization": userid + ":" + pswrd
    //         }
    //     });
    //     if (token) {
    //         onLogIn(token);
    //     }
    //     else {
    //         alert("There was an error logging in, but your username and password may be correct. Please try again");
    //     }
    // }
}

function hasGetUserMedia() {
    return !!(navigator.mediaDevices &&
        navigator.mediaDevices.getUserMedia);
}

function streamVideo(video){
    const constraints = {
        video: true
    };
    
    if (navigator.mediaDevices.getUserMedia)
    
    navigator.mediaDevices.getUserMedia(constraints).
        then((stream) => {video.srcObject = stream});
}

function screenshot(video, canvas){
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    // Other browsers will fall back to image/png
    return canvas.toDataURL('image/webp');
}

function recognize(image, token){
    return $.ajax({
        url: '/api/recognize',
        headers: {
            "Authorization": token
        }
    });
}

function onLogIn(token){
    document.getElementById("login").style.display = "none";
    document.getElementById("logged-in").style.display = "block";

    if (hasGetUserMedia()) {
        const video = document.querySelector('video');
        const canvas = document.createElement('canvas');

        streamVideo(video);

        window.setInterval(function(){
            var image = screenshot(video, canvas);
            
            

            // clearInterval() // stop looping
        }, 5000);
    } else {
        alert('getUserMedia() is not supported by your browser');
    }
}







  


