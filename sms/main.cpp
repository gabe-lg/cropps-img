#include <curl/curl.h>

#include <iostream>

#include "env.h"

void send_sms(std::string str) {
  CURL* curl;
  CURLcode res;
  curl = curl_easy_init();

  if (curl) {
    std::string url = "https://api.twilio.com/2010-04-01/Accounts/" +
                      account_sid + "/Messages.json";
    std::string post_fields =
        "To=" + to_number + "&From=" + from_number + "&Body=" + str;

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_USERNAME, account_sid.c_str());
    curl_easy_setopt(curl, CURLOPT_PASSWORD, auth_token.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, post_fields.c_str());
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION,
                     NULL);  // No response handling for simplicity

    res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
      std::cerr << "cURL error: " << curl_easy_strerror(res) << std::endl;
    }

    curl_easy_cleanup(curl);
  }
}

int main() {
  curl_global_init(CURL_GLOBAL_ALL);
  send_sms("hi");
  return 0;
}
