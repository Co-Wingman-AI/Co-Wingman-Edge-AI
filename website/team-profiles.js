"use strict";

// Publish only photos and public contact links supplied or confirmed by members.
// Photos should be local site assets; null keeps the initials placeholder.
const teamProfiles = {
  mrunal: {
    name: "Mrunal Vibhute",
    initials: "MV",
    role: "Project team",
    photo: null,
    links: [],
  },
  shrimayee: {
    name: "Shrimayee Deshpande",
    initials: "SD",
    role: "Project team",
    photo: null,
    links: [],
  },
  honey: {
    name: "Honey Reddy Daram",
    initials: "HD",
    role: "Project team",
    photo: "./assets/honey-reddy-daram.jpg",
    links: [
      {
        label: "Portfolio",
        url: "https://honeyreddydaram.github.io/Portfolio/",
      },
      {
        label: "LinkedIn",
        url: "https://www.linkedin.com/in/honeyreddydaram/",
      },
    ],
  },
  yasasvi: {
    name: "Yasasvi Kaipa",
    initials: "YK",
    role: "Project team",
    photo: null,
    links: [],
  },
  andrea: {
    name: "Dr. Andrea Ramirez-Salgado",
    initials: "AR",
    role: "Project advisor",
    photo: null,
    links: [],
  },
};
