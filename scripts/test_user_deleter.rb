#!/usr/bin/env ruby
# Simple script to nuke test users from a cognito idp pool
require 'optparse'
require 'json'

options = {}
OptionParser.new do |opts|
  opts.banner = "Usage: test_user_deleter.rb --poolId=<yourpoolid> --emails=<emailList>"
  opts.on("-p", "--poolId POOLID", "POOLID is required") do |p|
    options[:poolId] = p
  end
  options[:emails] = []
  opts.on("-e", "--emails EMAILS", "specify emails then will just do them") do |e|
    options[:emails] = e.split(',')
  end
end.parse!

def is_test_user(email)
  return email.start_with?('tuser') && email.end_with?('@uclusion.com')
end

def is_email_user(email, emails)
  return emails.include?(email)
end

poolId = options[:poolId]
emails = options[:emails]
puts("Listing users with #{poolId}")
users_response_string = `aws cognito-idp list-users --user-pool-id=#{poolId}`
users_response = JSON.parse(users_response_string)
users = users_response['Users']
puts users.size
users.each do |user|
  attributes = user['Attributes']
  id = user['Username']
  email_attr = attributes.find {|attr| attr['Name'] == 'email'}
  email = email_attr['Value']
  if !emails.empty? then
    isTest = is_email_user(email, emails)
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



