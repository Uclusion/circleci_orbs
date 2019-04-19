# Simple shell script to remove all api keys from the aws account
# USE WITH CAUTION

require 'json'
api_keys_string = `aws apigateway get-api-keys`
api_key_list = JSON.parse(api_keys_string)
api_keys = api_key_list["items"]
#puts api_keys.inspect
api_keys.each do |key_description|
  id = key_description["id"]
  puts "deleting api key #{id}"
  `aws apigateway delete-api-key --api-key #{id}`
end
return "done"
