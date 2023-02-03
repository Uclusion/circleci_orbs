#!/usr/bin/env ruby
# Simple script to nuke test users from a cognito idp pool
require 'optparse'
require 'json'

options = {}
OptionParser.new do |opts|
  opts.banner = "Usage: test_user_deleter.rb --poolId=<yourpoolid> --all"
  opts.on("-p", "--poolId POOLID", "POOLID is required") do |p|
    options[:poolId] = p
  end
  options[:all] = false
  opts.on("-a", "--all", "all is false by default") do
    options[:all] = true
  end
end.parse!

def is_test_user(email)
  return email.start_with?('tuser') && email.end_with?('@uclusion.com')
end

def is_not_integration_user(email)
  return !['david.israel@uclude.com', '827hooshang@gmail.com'].include?(email)
end

poolId = options[:poolId]
doAll = options[:all]

users_response_string = `aws cognito-idp list-users --user-pool-id=#{poolId}`
users_response = JSON.parse(users_response_string)
users = users_response['Users']
puts users.size
users.each do |user|
  attributes = user['Attributes']
  id = user['Username']
  email_attr = attributes.find {|attr| attr['Name'] == 'email'}
  email = email_attr['Value']
  if doAll then
    isTest = is_not_integration_user(email)
  else
    isTest = is_test_user(email)
  end
  if isTest then
    puts("Deleting user #{email} with user name #{id}")
    command = "aws cognito-idp admin-delete-user --user-pool-id=#{poolId} --username=#{id}"
    puts(command)
    `#{command}`
  end
end



