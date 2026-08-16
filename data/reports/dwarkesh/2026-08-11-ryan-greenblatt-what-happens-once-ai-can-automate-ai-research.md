# Ryan Greenblatt – What happens once AI can automate AI research?

- Kind: decision-support / time-saving notes from an official transcript
- Not a house view. No buy/sell. No investment-desk framing.
- Show: Dwarkesh Podcast
- Published: 2026-08-11
- Episode URL: https://www.dwarkesh.com/p/ryan-greenblatt
- Duration: 133 min
- Guest hint from title: Ryan Greenblatt
- Speakers in transcript: Dwarkesh Patel, Ryan Greenblatt
- Transcript source: https://www.dwarkesh.com/p/ryan-greenblatt
- Watched people named in title/description: none

## Main points

Attributed to the speaker. Wording is condensed from complete transcript sentences, not invented.

- **Ryan Greenblatt:** I would say that I expect full automation of AI R&D perhaps somewhere around 2031, 2030. Getting to the “beats all humans on the job” milestone, maybe my median expectation is around 2033. But if I see AIs fully automating AI R&D, I think I’m expecting that probably within a year. The way the forecasting works out, the difference between medians is bigger than the median difference between milestones.
- **Ryan Greenblatt:** I do think that the milestone for automating your video editor is earlier than the milestone of being able to automate all human jobs, including Texas politics, spinning up on the job. I do think that the video editor automation occurs maybe more around full automation of AI R&D, but it’s very sensitive to how much people are really focusing on understanding video. There’s a few different parts of this. One of them is that we can train on a bunch of environments which are basically directly training the model to do some AI R&D task or some very close-by task.
- **Dwarkesh Patel:** But I feel like one effect will be that we will have gotten rid of all the low-hanging fruits by 2030. I feel like scaling laws will have been, in math history, like Descartes finding the Cartesian grid and doing very basic mathematics. Eventually, if we want to keep making progress in the 2030s, it’s going to be like doing whatever bullshit is happening at the frontiers of mathematics right now.
- **Dwarkesh Patel:** I want to very concretely understand what it would look like for five years of AI progress to happen in one year. Suppose we were back when GPT-3 was developed. The idea is that, with the level of compute they had back in 2022, if we had automated AI R&D back then, you could at the end of that year have Mythos. Mythos took way more compute than they had back then, but even with the level of compute they had back then, not only do all the breakthroughs happen, but they also train Mythos with that level of compute.
- **Dwarkesh Patel:** I’m glad you brought that up, because what has happened since GPT-3, or even 3.5, till now? Why is Mythos so good? Obviously, we’ve scaled the compute. We have better algorithms.
- **Ryan Greenblatt:** But the question is what is the limiting factor on creating RL environments? My sense is that the reason why RL environments today are much better than they were in 2024 is not so much because we have hired way more human experts to make RL environments. It is instead much more because we better know what RL environments we even want to make and how we should structure them. Also, we’re using huge amounts of AI labor to build RL environments.
- **Dwarkesh Patel:** Just look at, for example, what was reported in Business Insider yesterday, that Google is paying close to $2 billion for Mechanize. We can just look at market rates for what people think really good human expert data is worth. The frontier labs seem to think it’s worth a lot. They’re willing to pay for it.
- **Dwarkesh Patel:** So maybe let’s be more concrete. Here’s what I think. My claim is that if you went back to 2022 and you had GPT-3.5, and you were trying to make it better at coding without human experts, I think it would have just been very, very difficult.
- **Dwarkesh Patel:** So we’re talking about how much progress has come from data versus algorithmic progress over the last few years. That reminds me, I’m actually running an experiment with this with Jerry Han, who’s still a college student. What we’re basically doing to evaluate how much progress is coming from data versus algorithms is training the best algorithmic recipe from 2019 till now with the best data from the 2026 data file, and then also training the different data files going back from 2019 to 2026 with the current best algorithmic recipe.
- **Ryan Greenblatt:** We need to be pretty careful with what we mean when we say the word data. I was trying to be pretty careful to distinguish between scaling up spending on getting human experts to label data, or scaling up the amount of human expert-labeled data. The reason why we have a better pre-training data set now versus in 2019 is not because people are spending way more money getting human experts to type up data that the AIs are then trained on. I think it’s not much of it.
- **Ryan Greenblatt:** There’s a complicated mix of factors. My view is more that people have done a bunch of big training runs that did not go that well. There’s GPT-4.5, which famously people at OpenAI thought was a bit of a bust. I think there are some rumors that there were a bunch of other training runs people have done that were a bit of a bust.
- **Dwarkesh Patel:** So let’s step back and package this whole story. I think people can probably follow along with this story. We have GPT-7.5 trained on a bunch of environments, where it’s not only in general becoming a better AI, but specifically we’re training it to do AI R&D better. It’s making GPT-2 size runs that are better at playing video games that require sample efficiency or online learning or whatever other capabilities.
- **Ryan Greenblatt:** Another thing that’s really important is you don’t just do GPT-2 sized runs, you also do small fine-tuning runs on GPT-6. As in, you have GPT-2, and you can do full pre-trains of GPT-2, and then you can do small post-training or mid-training or whatever runs on GPT-6. And then you can do a small number of experiments that are actually at frontier scale, but you do a bit of online training or something. Another thing we can do is take GPT-7.5, and presumably in the course of GPT-7.5’s work, it’s running a bunch of experiments at varying scale that are actually on the critical path for AI R&D.
- **Dwarkesh Patel:** Basically the thing you’re suggesting is: there’s the small-scale stuff where you’re teaching the AI to get better at AI R&D taste, but you’re discarding the actual “things it found”. Then it actually does real R&D in the practice of trying to become better at AI R&D, and you’re like, “This is a pretty cool thing that you discovered. Let’s actually also use this in production in the future, and teach you how to use it in production.” But stepping back, GPT-7.5 becomes GPT-8 as a result of all this AI R&D training and just generally becoming smarter. Then it helps you build GPT-9.
- **Dwarkesh Patel:** Stepping back, I buy the idea that you could have much faster AI R&D than we currently have. I’m not sure if you get GPT-3 to Mythos holding compute and data constant within a year, but suppose it’s half of that. If we even manage to continue the current trajectory of AI progress as a result of AI R&D, it would be fucking insane in five to ten years in ways that I don’t think people appreciate. I don’t think people appreciate what a big deal billions of AIs will be.
- **Dwarkesh Patel:** Right. So think back to GPT-4 basically. We’re talking about something that is to Mythos or Sol what Mythos is to GPT-4. This is where the situation is getting crazy.
- **Ryan Greenblatt:** This is a pretty big concern. One concern is that you pass off safety R&D to your AIs and what your AIs are doing is saying some stuff that sort of vaguely makes sense about the current safety situation. They write a report about risks that’s kind of sort of like what the report humans might have written. But they’re not really trying hard to have well-informed views, interrogate their assumptions, and try really hard to do that.
- **Ryan Greenblatt:** By 2040? Let’s see. Maybe around 35 or 40%? Yeah, it’s pretty high.

## Numbers they stated

- Dwarkesh Patel: Just look at, for example, what was reported in Business Insider yesterday, that Google is paying close to $2 billion for Mechanize.
- Ryan Greenblatt: Maybe around 35 or 40%?

## Caveats and disagreements

- Ryan Greenblatt: Getting to the “beats all humans on the job” milestone, maybe my median expectation is around 2033.
- Ryan Greenblatt: I do think that the video editor automation occurs maybe more around full automation of AI R&D, but it’s very sensitive to how much people are really focusing on understanding video.
- Dwarkesh Patel: But I feel like one effect will be that we will have gotten rid of all the low-hanging fruits by 2030.
- Dwarkesh Patel: I think it’s overwhelmingly compute, but I also think it’s because compute is easier to scale up than data.
- Dwarkesh Patel: So maybe let’s be more concrete.
- Ryan Greenblatt: We should maybe talk separately about mid-training and post-training.
- Ryan Greenblatt: But I think the vast majority of pre-training data improvements are from science on better understanding what data sets are good and schleppy labor on figuring out how to filter down.
- Ryan Greenblatt: Well, “a few” is maybe a bit understated.
- Dwarkesh Patel: Another very important thing has to happen, which is maybe the thing I’m most skeptical of.
- Dwarkesh Patel: I’m not sure if you get GPT-3 to Mythos holding compute and data constant within a year, but suppose it’s half of that.
- Ryan Greenblatt: Maybe around 35 or 40%?
- Dwarkesh Patel: So we’re talking about how much progress has come from data versus algorithmic progress over the last few years.
- Dwarkesh Patel: What we’re basically doing to evaluate how much progress is coming from data versus algorithms is training the best algorithmic recipe from 2019 till now with the best data from the 2026 data file, and then also training the different data files going back from 2019 to 2026 with the current best algorithmic recipe.
- Ryan Greenblatt: The reason why we have a better pre-training data set now versus in 2019 is not because people are spending way more money getting human experts to type up data that the AIs are then trained on.

## Notes

This file is an extractive main-points brief for later editing. If a claim is not in the transcript, it is not here.
