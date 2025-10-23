Write-Host "===== Test 200 OK ====="
curl.exe -v http://127.0.0.1:12000/test.html
Write-Host ""

Write-Host "===== Test 403 Forbidden ====="
curl.exe -v http://127.0.0.1:12000/testForbidden.html
Write-Host ""

Write-Host "===== Test 404 Not Found ====="
curl.exe -v http://127.0.0.1:12000/doesNotExist.html
Write-Host ""

Write-Host "===== Test 304 Not Modified ====="
curl.exe -v -H "If-Modified-Since: Thu, 01 Jan 2099 00:00:00 GMT" http://127.0.0.1:12000/test.html
Write-Host ""

Write-Host "===== Test 400 Bad Request ====="
curl.exe -v -X "BADMETHOD" http://127.0.0.1:12000/test.html
Write-Host ""
